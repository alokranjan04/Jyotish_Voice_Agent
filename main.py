import asyncio
import base64
import json
import os
import time
import websockets
try:
    import audioop
except ImportError:
    import audioop_lts as audioop
import traceback
from aiohttp import web
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"

def load_app_config():
    try:
        with open('app_config.json', 'r') as f:
            return json.load(f)
    except:
        return {"agent": {"system_prompt": "You are Jyotish Mitra, an expert Vedic astrologer."}}

APP_CONFIG = load_app_config()
SYSTEM_PROMPT = APP_CONFIG["agent"]["system_prompt"]
GREETING = APP_CONFIG.get("scripts", {}).get("greeting", "Namaste! Main aapki Jyotish Mitra hoon.")

async def home_page(request):
    return web.Response(text="Jyotish Voice Agent Online", content_type='text/plain')

async def handle_answer(request):
    """Answer the call and extract Caller ID from Vobiz POST body."""
    try:
        post_data = await request.post()
        raw_num = post_data.get("From") or post_data.get("CallerName") or "Unknown"
        caller_id = str(raw_num).replace("+", "").strip()
        if "sip:" in caller_id: caller_id = caller_id.split("sip:")[1].split("@")[0]
        
        host = request.headers.get("X-Forwarded-Host") or request.host
        ws_url = f"wss://{host}/vobiz-stream?caller_id={caller_id}"
        
        xml_response = f'<?xml version="1.0" encoding="UTF-8"?><Response><Stream bidirectional="true" keepCallAlive="true" contentType="audio/x-mulaw;rate=8000">{ws_url}</Stream></Response>'
        print(f"\n[INCOMING] -> Caller ID: {caller_id}")
        return web.Response(text=xml_response, content_type='text/xml')
    except Exception:
        return web.Response(text="Error", status=500)

async def vobiz_handler(request):
    caller_id = request.query.get("caller_id", "Unknown")
    ws = web.WebSocketResponse(protocols=['audio.drachtio.org'])
    await ws.prepare(request)
    print(f"--- [BRIDGE]: Ready for Caller {caller_id} ---")
    
    start_time = time.time()
    state = {"last_ai_audio_time": 0}
    
    try:
        print(f"--- [AI ENGINE]: Connecting to Gemini... ---")
        async with websockets.connect(GEMINI_URL) as gemini_ws:
            # Setup
            current_date_str = datetime.now().strftime("%A, %B %d, %Y")
            dynamic_prompt = f"{SYSTEM_PROMPT}\n\nIMPORTANT: Be calm and empathetic. Caller number: {caller_id}. Today is: {current_date_str}."
            
            # Use 1.5 Flash for maximum stability first
            setup_msg = {
                "setup": {
                    "model": "models/gemini-1.5-flash",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Aoede"}}}
                    },
                    "systemInstruction": {"parts": [{"text": dynamic_prompt}]},
                    "inputAudioTranscription": {},
                    "outputAudioTranscription": {}
                }
            }
            print(f"--- [AI ENGINE]: Sending Setup... ---")
            await gemini_ws.send(json.dumps(setup_msg))
            setup_resp = await gemini_ws.recv()
            print(f"--- [AI ENGINE]: Setup Response: {setup_resp[:200]} ---")

            # Trigger greeting
            await gemini_ws.send(json.dumps({"realtimeInput": {"text": "Hello"}}))
            
            stream_sid = None
            upsample_state = None 

            async def from_vobiz():
                nonlocal stream_sid, upsample_state
                try:
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            current_id = data.get("streamId") or data.get("streamSid") or (data.get("start", {}).get("streamId") if data.get("event") == "start" else None)
                            if current_id and not stream_sid: stream_sid = current_id

                            if data.get("event") == "media" and stream_sid:
                                if time.time() - state["last_ai_audio_time"] < 1.0: continue
                                payload = data.get("media", {}).get("payload") or data.get("payload")
                                if payload:
                                    mulaw_data = base64.b64decode(payload)
                                    pcm_8k = audioop.ulaw2lin(mulaw_data, 2)
                                    pcm_16k, upsample_state = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, upsample_state)
                                    await gemini_ws.send(json.dumps({"realtimeInput": {"audio": {"data": base64.b64encode(pcm_16k).decode("utf-8"), "mimeType": "audio/pcm;rate=16000"}}}))
                        elif msg.type == aiohttp.WSMsgType.CLOSE: break
                except Exception as e:
                    print(f"[ERROR] from_vobiz: {e}")

            downsample_state = None 

            async def from_gemini():
                nonlocal downsample_state
                try:
                    async for message in gemini_ws:
                        resp = json.loads(message)
                        
                        # Transcriptions
                        transcription = resp.get("serverContent", {}).get("inputAudioTranscription", {}).get("text")
                        if transcription: print(f"\n[USER]: {transcription}")
                        
                        out_transcription = resp.get("serverContent", {}).get("outputAudioTranscription", {}).get("text")
                        if out_transcription: print(f"\n[JYOTISH]: {out_transcription}")

                        # Audio
                        server_content = resp.get("serverContent")
                        if server_content:
                            model_turn = server_content.get("modelTurn")
                            if model_turn:
                                for part in model_turn.get("parts", []):
                                    if "inlineData" in part:
                                        state["last_ai_audio_time"] = time.time()
                                        pcm_24k = base64.b64decode(part["inlineData"]["data"])
                                        pcm_8k, downsample_state = audioop.ratecv(pcm_24k, 2, 1, 24000, 8000, downsample_state)
                                        mulaw_data = audioop.lin2ulaw(pcm_8k, 2)
                                        if stream_sid:
                                            await ws.send_str(json.dumps({
                                                "event": "playAudio", "streamId": stream_sid, 
                                                "media": {"contentType": "audio/x-mulaw", "sampleRate": 8000, "payload": base64.b64encode(mulaw_data).decode("utf-8")}
                                            }))
                except Exception as e:
                    print(f"[ERROR] from_gemini: {e}")

            await asyncio.wait([asyncio.create_task(from_vobiz()), asyncio.create_task(from_gemini())], return_when=asyncio.FIRST_COMPLETED)

    except Exception as e:
        print(f"[ERROR] vobiz_handler: {e}")
    finally:
        if not ws.closed: await ws.close()
    return ws

async def main():
    app = web.Application()
    app.router.add_get('/', home_page)
    app.router.add_post('/answer', handle_answer)
    app.router.add_get('/vobiz-stream', vobiz_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "5051"))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print("╔══════════════════════════════════════════════════════════╗")
    print(f"║  JYOTISH VOICE AGENT ONLINE (PORT {port})                  ║")
    print("╚══════════════════════════════════════════════════════════╝")
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
