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
        
        # XML Response exactly as Priya's
        xml_response = f'<?xml version="1.0" encoding="UTF-8"?><Response><Stream bidirectional="true" keepCallAlive="true">{ws_url}</Stream></Response>'
        print(f"\n[INCOMING] -> Caller ID: {caller_id}")
        return web.Response(text=xml_response, content_type='text/xml')
    except Exception:
        return web.Response(text="Error", status=500)

async def vobiz_handler(request):
    caller_id = request.query.get("caller_id", "Unknown")
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print(f"--- [BRIDGE]: Connected to Caller {caller_id} ---")
    
    state = {"last_ai_audio_time": 0}
    
    try:
        async with websockets.connect(GEMINI_URL) as gemini_ws:
            # Setup Gemini (using Priya's model)
            current_date_str = datetime.now().strftime("%A, %B %d, %Y")
            dynamic_prompt = f"{SYSTEM_PROMPT}\n\nIMPORTANT: Be calm and empathetic. Caller number: {caller_id}. Today is: {current_date_str}."
            
            setup_msg = {
                "setup": {
                    "model": "models/gemini-3.1-flash-live-preview",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Aoede"}}}
                    },
                    "systemInstruction": {"parts": [{"text": dynamic_prompt}]},
                    "inputAudioTranscription": {},
                    "outputAudioTranscription": {}
                }
            }
            await gemini_ws.send(json.dumps(setup_msg))
            setup_resp = await gemini_ws.recv()
            print(f"--- [AI ENGINE]: Setup success ---")

            # Trigger greeting as Priya does
            await gemini_ws.send(json.dumps({"realtimeInput": {"text": "Hello"}}))
            print(f"--- [AI ENGINE]: Greeting Trigger Sent ---")

            stream_sid = None
            upsample_state = None

            async def vobiz_to_ai():
                nonlocal stream_sid, upsample_state
                try:
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            
                            # Catch the Stream SID
                            current_id = data.get("streamId") or data.get("streamSid") or (data.get("start", {}).get("streamId") if data.get("event") == "start" else None)
                            if current_id and not stream_sid: 
                                stream_sid = current_id
                                print(f"--- [VOBIZ]: Stream SID identified: {stream_sid} ---")

                            if data.get("event") == "media" and stream_sid:
                                payload = data.get("media", {}).get("payload") or data.get("payload")
                                if payload:
                                    mulaw_data = base64.b64decode(payload)
                                    pcm_8k = audioop.ulaw2lin(mulaw_data, 2)
                                    pcm_16k, upsample_state = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, upsample_state)
                                    # Use Priya's "audio" key
                                    await gemini_ws.send(json.dumps({
                                        "realtimeInput": {
                                            "audio": {
                                                "data": base64.b64encode(pcm_16k).decode("utf-8"),
                                                "mimeType": "audio/pcm;rate=16000"
                                            }
                                        }
                                    }))
                except Exception as e:
                    print(f"Error in vobiz_to_ai: {e}")

            downsample_state = None

            async def ai_to_vobiz():
                nonlocal downsample_state
                audio_packet_count = 0
                try:
                    async for message in gemini_ws:
                        resp = json.loads(message)
                        
                        # Visible Transcript logging
                        server_content = resp.get("serverContent")
                        if server_content:
                            # User speech transcript
                            user_trans = server_content.get("inputAudioTranscription", {}).get("text")
                            if user_trans: print(f"\n>>> [USER]: {user_trans}")
                            
                            # AI speech transcript
                            ai_trans = server_content.get("outputAudioTranscription", {}).get("text")
                            if ai_trans: print(f"\n>>> [AI]: {ai_trans}")

                            if "modelTurn" in server_content:
                                parts = server_content["modelTurn"].get("parts", [])
                                for part in parts:
                                    if "inlineData" in part:
                                        audio_packet_count += 1
                                        state["last_ai_audio_time"] = time.time()
                                        
                                        # Gemini default is 24kHz. Treating as 16kHz caused the 'man voice'
                                        pcm_24k = base64.b64decode(part["inlineData"]["data"])
                                        pcm_8k, downsample_state = audioop.ratecv(pcm_24k, 2, 1, 24000, 8000, downsample_state)
                                        ulaw_data = audioop.lin2ulaw(pcm_8k, 2)
                                        
                                        if stream_sid:
                                            await ws.send_str(json.dumps({
                                                "event": "playAudio",
                                                "streamId": stream_sid,
                                                "media": {
                                                    "contentType": "audio/x-mulaw",
                                                    "sampleRate": 8000,
                                                    "payload": base64.b64encode(ulaw_data).decode("utf-8")
                                                }
                                            }))
                except Exception as e:
                    print(f"Error in ai_to_vobiz: {e}")

            await asyncio.gather(vobiz_to_ai(), ai_to_vobiz())

    except Exception as e:
        print(f"--- [CRITICAL ERROR]: {e} ---")
        traceback.print_exc()
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
