#!/usr/bin/env python3
"""
OpenClaw Voice Hotkey Assistant
Press Cmd+Shift+Space → speak → get AI response
"""

import json
import subprocess
import tempfile
import os
import sys
import time
from pathlib import Path
from pynput import keyboard
import pyaudio
import wave
import asyncio
import websockets

# Load config
CONFIG_FILE = Path(__file__).parent / "config.json"
with open(CONFIG_FILE) as f:
    CONFIG = json.load(f)

# State
is_recording = False
audio_frames = []
audio_stream = None
p = None
recording_start_time = None

def start_recording():
    """Start audio recording"""
    global is_recording, audio_frames, audio_stream, p, recording_start_time
    
    if is_recording:
        return
    
    print("🎤 Recording started...")
    is_recording = True
    audio_frames = []
    recording_start_time = time.time()
    
    # Initialize PyAudio
    p = pyaudio.PyAudio()
    audio_stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        frames_per_buffer=1024,
        stream_callback=audio_callback
    )
    audio_stream.start_stream()

def audio_callback(in_data, frame_count, time_info, status):
    """Callback for audio stream"""
    global audio_frames
    audio_frames.append(in_data)
    return (in_data, pyaudio.paContinue)

def stop_recording():
    """Stop recording and process"""
    global is_recording, audio_stream, p, recording_start_time
    
    if not is_recording:
        return
    
    # Check minimum recording duration
    duration = time.time() - recording_start_time if recording_start_time else 0
    
    print(f"⏸️  Recording stopped (duration: {duration:.1f}s)")
    is_recording = False
    
    # Stop stream
    if audio_stream:
        audio_stream.stop_stream()
        audio_stream.close()
    if p:
        p.terminate()
    
    # Skip if recording was too short (< 0.5 seconds)
    if duration < 0.5:
        print("⚠️  Recording too short, skipping...")
        return
    
    # Save audio to temp file
    audio_file = save_audio()
    
    # Transcribe with Whisper
    print("🔄 Transcribing...")
    text = transcribe_audio(audio_file)
    
    if not text or text.strip() == "":
        print("⚠️  No speech detected")
        return
    
    print(f"📝 Transcription: {text}")
    
    # Send to OpenClaw
    print("🤖 Sending to OpenClaw...")
    response = asyncio.run(send_to_openclaw(text))
    
    if response:
        print(f"💬 Response: {response}")
        speak_text(response)

def save_audio():
    """Save audio frames to WAV file"""
    global audio_frames
    
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    
    wf = wave.open(temp_file.name, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
    wf.setframerate(16000)
    wf.writeframes(b''.join(audio_frames))
    wf.close()
    
    return temp_file.name

def transcribe_audio(audio_file):
    """Transcribe audio using Whisper CLI"""
    try:
        model = CONFIG.get("whisperModel", "base")
        result = subprocess.run(
            ["whisper", audio_file, "--model", model, "--output_format", "txt", "--language", "en"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Whisper writes output to <audio_file>.txt
        txt_file = audio_file.replace(".wav", ".txt")
        if os.path.exists(txt_file):
            with open(txt_file) as f:
                text = f.read().strip()
            os.remove(txt_file)
            return text
        
        return None
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return None
    finally:
        # Clean up audio file
        if os.path.exists(audio_file):
            os.remove(audio_file)

async def send_to_openclaw(text):
    """Send message to OpenClaw gateway"""
    gateway_url = CONFIG.get("openclawGateway", "ws://127.0.0.1:18789")
    
    try:
        async with websockets.connect(gateway_url) as websocket:
            # Send message (format depends on OpenClaw protocol)
            message = {
                "type": "chat.send",
                "message": text
            }
            await websocket.send(json.dumps(message))
            
            # Receive response
            response = await websocket.recv()
            data = json.loads(response)
            
            # Extract text from response (adjust based on OpenClaw protocol)
            return data.get("text", str(data))
    
    except Exception as e:
        print(f"❌ OpenClaw error: {e}")
        return None

def speak_text(text):
    """Speak text using TTS"""
    tts_engine = CONFIG.get("ttsEngine", "say")
    
    try:
        if tts_engine == "say":
            subprocess.run(["say", text])
        elif tts_engine == "sag":
            subprocess.run(["sag", text])
        elif tts_engine == "piper":
            piper_binary = CONFIG.get("piperBinary", "./bin/piper")
            
            # Auto-select model based on language
            language = CONFIG.get("language", "uk")
            if language == "uk":
                piper_model = CONFIG.get("piperModelUK", "./models/tts/uk_UA-lada-x_low.onnx")
            elif language == "en":
                piper_model = CONFIG.get("piperModelEN", "./models/tts/en_US-lessac-medium.onnx")
            else:
                # Fallback to explicit piperModel or default
                piper_model = CONFIG.get("piperModel", "./models/tts/uk_UA-lada-x_low.onnx")
            
            # Piper: echo "text" | piper --model model.onnx --output_file output.wav && afplay output.wav
            temp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            
            # Generate audio with piper
            proc = subprocess.Popen(
                [piper_binary, "--model", piper_model, "--output_file", temp_audio.name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            proc.communicate(input=text.encode('utf-8'))
            
            # Play audio
            subprocess.run(["afplay", temp_audio.name])
            
            # Clean up
            os.remove(temp_audio.name)
        else:
            print(f"⚠️  Unknown TTS engine: {tts_engine}")
    except Exception as e:
        print(f"❌ TTS error: {e}")

# Track modifier keys state
current_modifiers = set()

def on_press(key):
    """Handle key press"""
    try:
        # Track modifier keys
        if key == keyboard.Key.cmd or key == keyboard.Key.cmd_r:
            current_modifiers.add('cmd')
        elif key == keyboard.Key.shift or key == keyboard.Key.shift_r:
            current_modifiers.add('shift')
        
        # Check for Cmd+Shift+Space combination
        if key == keyboard.Key.space:
            if 'cmd' in current_modifiers and 'shift' in current_modifiers:
                print("🎤 Hotkey detected: Cmd+Shift+Space")
                start_recording()
    except AttributeError:
        pass

def on_release(key):
    """Handle key release"""
    try:
        # Remove released modifiers
        if key == keyboard.Key.cmd or key == keyboard.Key.cmd_r:
            current_modifiers.discard('cmd')
        elif key == keyboard.Key.shift or key == keyboard.Key.shift_r:
            current_modifiers.discard('shift')
        
        # Stop recording when Space is released (if we were recording)
        if key == keyboard.Key.space and is_recording:
            stop_recording()
        
        # Exit on Escape
        if key == keyboard.Key.esc:
            print("\n👋 Exiting...")
            return False
    except AttributeError:
        pass

def main():
    """Main entry point"""
    print("🎙️  OpenClaw Voice Hotkey Assistant")
    print(f"📍 Gateway: {CONFIG['openclawGateway']}")
    print(f"🔑 Hotkey: {CONFIG['hotkey']}")
    print("Press Cmd+Shift+Space to record, Escape to exit")
    print()
    
    # Start listening for hotkeys
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    main()
