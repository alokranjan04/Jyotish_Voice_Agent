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
from email_utils import send_astrology_report

load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_URL = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"
MEMORY_FILE = "user_memory.json"

def load_app_config():
    try:
        with open('app_config.json', 'r') as f:
            return json.load(f)
    except:
        return {"agent": {"system_prompt": "You are Jyotish Mitra, an expert Vedic astrologer."}}

def load_user_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except: return {}
    return {}

def save_user_memory(memory):
    try:
        with open(MEMORY_FILE, 'w') as f:
            json.dump(memory, f)
    except Exception as e:
        print(f"[ERROR] Saving memory: {e}")

APP_CONFIG = load_app_config()
SYSTEM_PROMPT = APP_CONFIG["agent"]["system_prompt"]

async def home_page(request):
    return web.Response(text="Jyotish Voice Agent Online", content_type='text/plain')

async def handle_answer(request):
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
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print(f"--- [BRIDGE]: Connected to Caller {caller_id} ---")
    
    state = {"last_ai_audio_time": 0, "transcript": []}
    memory = load_user_memory()
    user_data = memory.get(caller_id)
    
    try:
        async with websockets.connect(GEMINI_URL) as gemini_ws:
            current_date_str = datetime.now().strftime("%A, %B %d, %Y")
            
            # Smart context for returning users
            memory_context = ""
            if user_data:
                memory_context = f"\n\nRETURNING USER DETECTED:\nName: {user_data.get('name')}\nBirth Details: {user_data.get('birth_details')}\nEmail: {user_data.get('email')}\n\nINSTRUCTION: Since this is a returning user, start by saying: 'Namaste {user_data.get('name')} ji! Last time you called for an astrology consultation and I sent your report to {user_data.get('email')}. Kya aap apne baare mein aur jaanna chahte hain ya aapko kisi aur ki kundali banwali hai?'"
            
            dynamic_prompt = f"{SYSTEM_PROMPT}{memory_context}\n\nIMPORTANT: Be calm and empathetic. Caller number: {caller_id}. Today is: {current_date_str}."
            
            TOOLS = [{
                "function_declarations": [{
                    "name": "send_astrology_report",
                    "description": "Sends an astrology report email to the user.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to_email": {"type": "string", "description": "User's email address"},
                            "name": {"type": "string", "description": "User's name"},
                            "birth_details": {"type": "string", "description": "Full birth details"},
                            "analysis": {"type": "string", "description": "The astrological analysis summary."}
                        },
                        "required": ["to_email", "name", "birth_details", "analysis"]
                    }
                },
                {
                    "name": "save_user_profile",
                    "description": "Saves the user's name, birth details, and email to memory for future calls.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "birth_details": {"type": "string"},
                            "email": {"type": "string"}
                        },
                        "required": ["name", "birth_details", "email"]
                    }
                }]
            }]

            setup_msg = {
                "setup": {
                    "model": "models/gemini-3.1-flash-live-preview",
                    "generationConfig": {
                        "responseModalities": ["AUDIO"],
                        "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Aoede"}}}
                    },
                    "systemInstruction": {"parts": [{"text": dynamic_prompt}]},
                    "tools": TOOLS,
                    "inputAudioTranscription": {},
                    "outputAudioTranscription": {}
                }
            }
            await gemini_ws.send(json.dumps(setup_msg))
            await gemini_ws.recv()
            print(f"--- [AI ENGINE]: Setup success ---")

            # Greeting trigger
            trigger_text = "Start the session." if not user_data else f"Greet the returning user {user_data.get('name')}."
            await gemini_ws.send(json.dumps({"realtimeInput": {"text": trigger_text}}))

            stream_sid = None
            upsample_state = None

            async def vobiz_to_ai():
                nonlocal stream_sid, upsample_state
                try:
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            current_id = data.get("streamId") or data.get("streamSid") or (data.get("start", {}).get("streamId") if data.get("event") == "start" else None)
                            if current_id and not stream_sid: stream_sid = current_id

                            if data.get("event") == "media" and stream_sid:
                                payload = data.get("media", {}).get("payload") or data.get("payload")
                                if payload:
                                    mulaw_data = base64.b64decode(payload)
                                    pcm_8k = audioop.ulaw2lin(mulaw_data, 2)
                                    pcm_16k, upsample_state = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, upsample_state)
                                    await gemini_ws.send(json.dumps({"realtimeInput": {"audio": {"data": base64.b64encode(pcm_16k).decode("utf-8"), "mimeType": "audio/pcm;rate=16000"}}}))
                except Exception as e: print(f"Error in vobiz_to_ai: {e}")

            downsample_state = None

            async def ai_to_vobiz():
                nonlocal downsample_state
                try:
                    async for message in gemini_ws:
                        resp = json.loads(message)
                        
                        if "toolCall" in resp:
                            for call in resp["toolCall"]["functionCalls"]:
                                if call["name"] == "send_astrology_report":
                                    args = call["args"]
                                    full_transcript = "\n".join(state["transcript"])
                                    success = send_astrology_report(args['to_email'], args['name'], args['birth_details'], args['analysis'], full_transcript)
                                    await gemini_ws.send(json.dumps({"toolResponse": {"functionResponses": [{"name": "send_astrology_report", "id": call["id"], "response": {"result": "Success" if success else "Failed"}}]}}))
                                
                                elif call["name"] == "save_user_profile":
                                    args = call["args"]
                                    memory[caller_id] = args
                                    save_user_memory(memory)
                                    print(f"--- [MEMORY]: Saved profile for {caller_id} ---")
                                    await gemini_ws.send(json.dumps({"toolResponse": {"functionResponses": [{"name": "save_user_profile", "id": call["id"], "response": {"result": "Saved"}}]}}))

                        server_content = resp.get("serverContent")
                        if server_content:
                            user_trans = server_content.get("inputAudioTranscription", {}).get("text")
                            if user_trans:
                                print(f">>> [USER]: {user_trans}")
                                state["transcript"].append(f"User: {user_trans}")
                            
                            ai_trans = server_content.get("outputAudioTranscription", {}).get("text")
                            if ai_trans:
                                print(f">>> [AI]: {ai_trans}")
                                state["transcript"].append(f"Jyotish Mitra: {ai_trans}")

                            if "modelTurn" in server_content:
                                for part in server_content["modelTurn"].get("parts", []):
                                    if "inlineData" in part:
                                        state["last_ai_audio_time"] = time.time()
                                        pcm_24k = base64.b64decode(part["inlineData"]["data"])
                                        pcm_8k, downsample_state = audioop.ratecv(pcm_24k, 2, 1, 24000, 8000, downsample_state)
                                        mulaw_data = audioop.lin2ulaw(pcm_8k, 2)
                                        if stream_sid:
                                            await ws.send_str(json.dumps({"event": "playAudio", "streamId": stream_sid, "media": {"contentType": "audio/x-mulaw", "sampleRate": 8000, "payload": base64.b64encode(mulaw_data).decode("utf-8")}}))
                except Exception as e: print(f"Error in ai_to_vobiz: {e}")

            await asyncio.gather(vobiz_to_ai(), ai_to_vobiz())

    except Exception as e: traceback.print_exc()
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
    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    while True: await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
