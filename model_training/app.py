import gradio as gr
import whisper
import asyncio
import fastapi_poe as fp
import json
import socket

# ------------------------------
# CONFIG
# ------------------------------

SYSTEM_PROMPT = """
You are a voice assistant for a smart personal assistant.
Given a voice command, output ONLY one of:
AUTO_MODE
STUDY
RELAX
SLEEP
AWAY
ERROR

Needs to be in all caps.
"""

POE_API_KEY = "TRyXJBFHRo6v5VhfF7h2ZNwB7NxNXg_WRJAMEQzxFxc"
whisper_model = whisper.load_model("tiny.en")

ESP_IP = "192.168.1.34"   # <- You will replace later
PORT = 80

# ------------------------------
# LLM CALL
# ------------------------------

async def get_llm_mode_label(prompt: str) -> str:
    """
    Sends transcription to POE LLM.
    Should return one of:
       study_mode / relax_mode / sleep_mode / away_mode / error
    """
    sys_msg = fp.ProtocolMessage(role="system", content=SYSTEM_PROMPT)
    user_msg = fp.ProtocolMessage(role="user", content=prompt)
    full_output = ""

    async for chunk in fp.get_bot_response(
        messages=[sys_msg, user_msg],
        bot_name="GPT-4o-Mini",
        api_key=POE_API_KEY
    ):
        full_output += chunk.text

    return full_output.strip().lower()

# ------------------------------
# ESP32 COMMUNICATION
# ------------------------------

def send_to_esp32(mode: str, transcription: str):
    """
    Sends {"mode": "<mode>", "transcription": "<text>"} to the ESP32.
    """

    payload = {
        "mode": mode,
        "transcription": transcription
    }

    data = json.dumps(payload).encode()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)

    try:
        s.connect((ESP_IP, PORT))
        s.sendall(data)
        response = s.recv(1024).decode()
        return f"ESP32 Response: {response}"

    except Exception as e:
        return f"❌ Error sending to ESP32: {e}"

    finally:
        s.close()

# ------------------------------
# MAIN LOGIC
# ------------------------------

def process_audio(audio_path):
    if audio_path is None:
        return "No audio.", "", ""

    # Transcribe
    try:
        result = whisper_model.transcribe(audio_path)
        transcription = result["text"].strip()
    except Exception as e:
        return f"❌ Whisper error: {e}", "", ""

    # Send to LLM
    try:
        mode_label = asyncio.run(get_llm_mode_label(transcription))
    except Exception as e:
        return transcription, f"❌ LLM error: {e}", ""

    # Send to ESP32
    esp_response = send_to_esp32(mode_label, transcription)

    return transcription, mode_label, esp_response

# ------------------------------
# GRADIO UI
# ------------------------------

ui = gr.Interface(
    fn=process_audio,
    inputs=[gr.Audio(sources=["microphone"], type="filepath", label="🎤 Voice Command")],
    outputs=[
        gr.Textbox(label="📝 Transcription"),
        gr.Textbox(label="🤖 LLM Mode Output"),
        gr.Textbox(label="📡 ESP32 Response")
    ],
    title="ESP32 Voice Mode Controller",
    description="Speak a command such as 'set study mode' or 'I'm going to sleep'. The app transcribes your voice, predicts the mode, and sends it to your ESP32 device.",
    allow_flagging="never",
)

if __name__ == "__main__":
    ui.launch(debug=False, share=True)
