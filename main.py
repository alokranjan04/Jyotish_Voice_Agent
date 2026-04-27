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
        caller_id = str(raw_num).replace("+", "").replace("sip:", "").split("@")[0].strip()
        if caller_id.startswith("91") and len(caller_id) > 10: caller_id = caller_id[2:]
        host = request.headers.get("X-Forwarded-Host") or request.host
        ws_url = f"wss://{host}/vobiz-stream?caller_id={caller_id}"
        xml_response = f'<?xml version="1.0" encoding="UTF-8"?><Response><Stream bidirectional="true" keepCallAlive="true" contentType="audio/x-mulaw;rate=8000">{ws_url}</Stream></Response>'
        return web.Response(text=xml_response, content_type='text/xml')
    except Exception: return web.Response(text="Error", status=500)

async def vobiz_handler(request):
    caller_id = request.query.get("caller_id", "Unknown")
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print(f"--- [BRIDGE]: Connected to Caller {caller_id} ---")
    
    state = {"last_ai_audio_time": 0, "transcript": [], "captured_email": None, "user_name": "User", "greeted": False, "dob": "N/A", "tob": "N/A", "pob": "N/A"}
    memory = load_user_memory()
    user_data = memory.get(caller_id)
    if user_data: 
        state["captured_email"] = user_data.get("email")
        state["user_name"] = user_data.get("name")
        state["dob"] = user_data.get("dob", "N/A")
        state["tob"] = user_data.get("tob", "N/A")
        state["pob"] = user_data.get("pob", "N/A")
    
    try:
        while not ws.closed:
            try:
                async with websockets.connect(GEMINI_URL) as gemini_ws:
                    current_date_str = datetime.now().strftime("%A, %B %d, %Y")
                    memory_context = ""
                    if user_data:
                        memory_context = f"\n\nRETURNING USER DETECTED:\nName: {user_data.get('name')}\nDOB: {user_data.get('dob')}\nTOB: {user_data.get('tob')}\nPOB: {user_data.get('pob')}\nEmail: {user_data.get('email')}"
                    
                    dynamic_prompt = f"{SYSTEM_PROMPT}{memory_context}\n\nCaller: {caller_id}. Today: {current_date_str}."
                    
                    TOOLS = [{
                        "function_declarations": [{
                            "name": "send_astrology_report",
                            "description": "Sends the premium Kundali HTML report to the user's email. Call this after the user confirms their email and you have completed the astrological analysis.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "to_email": {"type": "string", "description": "User's email address"},
                                    "name": {"type": "string", "description": "User's full name"},
                                    "dob": {"type": "string", "description": "Date of birth"},
                                    "tob": {"type": "string", "description": "Time of birth"},
                                    "pob": {"type": "string", "description": "Place of birth"},
                                    "planets": {"type": "string", "description": "Planet house positions calculated from birth details. Format: Sun=X,Moon=X,Mars=X,Mercury=X,Jupiter=X,Venus=X,Saturn=X,Rahu=X,Ketu=X where X is house number 1-12"},
                                    "analysis_html": {"type": "string", "description": "Full Hindi Kundali analysis in HTML with h2 headings for each section"}
                                },
                                "required": ["to_email", "name", "dob", "tob", "pob", "planets", "analysis_html"]
                            }
                        },
                        {
                            "name": "save_user_profile",
                            "description": "Saves user profile.",
                            "parameters": {
                                "type": "object",
                                "properties": {"name": {"type": "string"}, "dob": {"type": "string"}, "tob": {"type": "string"}, "pob": {"type": "string"}, "email": {"type": "string"}},
                                "required": ["name", "dob", "tob", "pob", "email"]
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
                            "inputAudioTranscription": {}, "outputAudioTranscription": {}
                        }
                    }
                    await gemini_ws.send(json.dumps(setup_msg))
                    await gemini_ws.recv()
                    
                    if not state["greeted"]:
                        trigger = "Greet the returning user." if user_data else "Start the new session."
                        await gemini_ws.send(json.dumps({"realtimeInput": {"text": trigger}}))
                        state["greeted"] = True

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
                                elif msg.type == aiohttp.WSMsgType.CLOSE: break
                        except Exception: pass

                    async def ai_to_vobiz():
                        nonlocal downsample_state
                        try:
                            async for message in gemini_ws:
                                resp = json.loads(message)
                                if "toolCall" in resp:
                                    for call in resp["toolCall"]["functionCalls"]:
                                        if call["name"] == "send_astrology_report":
                                            args = call["args"]
                                            state["captured_email"] = args['to_email']
                                            state["user_name"] = args['name']
                                            state["dob"], state["tob"], state["pob"] = args['dob'], args['tob'], args['pob']
                                            asyncio.create_task(asyncio.to_thread(send_astrology_report, args['to_email'], args['name'], args['dob'], args['tob'], args['pob'], args['analysis_html'], args.get('planets', '')))
                                            await gemini_ws.send(json.dumps({"toolResponse": {"functionResponses": [{"name": "send_astrology_report", "id": call["id"], "response": {"result": "Success"}}]}}))
                                        elif call["name"] == "save_user_profile":
                                            args = call["args"]
                                            memory[caller_id] = args
                                            save_user_memory(memory)
                                            await gemini_ws.send(json.dumps({"toolResponse": {"functionResponses": [{"name": "save_user_profile", "id": call["id"], "response": {"result": "Saved"}}]}}))
                                server_content = resp.get("serverContent")
                                if server_content:
                                    # Barge-in: Gemini detected user interrupted mid-response
                                    if server_content.get("interrupted") and stream_sid:
                                        await ws.send_str(json.dumps({"event": "clearAudio", "streamId": stream_sid}))
                                    user_trans = server_content.get("inputAudioTranscription", {}).get("text")
                                    if user_trans:
                                        if stream_sid: await ws.send_str(json.dumps({"event": "clearAudio", "streamId": stream_sid}))
                                        state["transcript"].append(f"User: {user_trans}")
                                    ai_trans = server_content.get("outputAudioTranscription", {}).get("text")
                                    if ai_trans: state["transcript"].append(f"Jyotish Mitra: {ai_trans}")
                                    if "modelTurn" in server_content:
                                        for part in server_content["modelTurn"].get("parts", []):
                                            if "inlineData" in part:
                                                pcm_24k = base64.b64decode(part["inlineData"]["data"])
                                                pcm_8k, downsample_state = audioop.ratecv(pcm_24k, 2, 1, 24000, 8000, downsample_state)
                                                mulaw_data = audioop.lin2ulaw(pcm_8k, 2)
                                                if stream_sid: await ws.send_str(json.dumps({"event": "playAudio", "streamId": stream_sid, "media": {"contentType": "audio/x-mulaw", "sampleRate": 8000, "payload": base64.b64encode(mulaw_data).decode("utf-8")}}))
                        except Exception: pass

                    downsample_state = None
                    async def heartbeat():
                        while not ws.closed:
                            await asyncio.sleep(30)
                            try: await gemini_ws.ping()
                            except: break
                    await asyncio.gather(vobiz_to_ai(), ai_to_vobiz(), heartbeat())
            except Exception: await asyncio.sleep(1)
    except Exception: traceback.print_exc()
    finally:
        # ENSURE Transcript is sent before closing
        if state["captured_email"] and len(state["transcript"]) > 2:
            print(f"--- [POST-CALL]: Sending transcript to {state['captured_email']} ---")
            full_text = "<br>".join(state["transcript"])
            # USE AWAIT here to ensure it finishes before the coroutine exits
            await asyncio.to_thread(send_astrology_report, state["captured_email"], state["user_name"], state["dob"], state["tob"], state["pob"], "<p>See transcript below.</p>", "", full_text)
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
