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
import asyncio
from pathlib import Path
from pynput import keyboard
import pyaudio
import wave
from openclaw_client import OpenClawClient

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
    
    # Get input device
    configured_device = CONFIG.get("inputDevice")
    input_device_index = configured_device if configured_device is not None else None
    
    if input_device_index is not None:
        device_info = p.get_device_info_by_index(input_device_index)
        print(f"   Using device [{input_device_index}]: {device_info['name']}")
    
    audio_stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=16000,
        input=True,
        input_device_index=input_device_index,
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
    
    # Send to OpenClaw and get response
    print("🤖 Sending to OpenClaw...")
    response = send_to_openclaw(text)
    
    if response:
        print(f"💬 Response: {response[:100]}...")
        # Speak the response using TTS
        print("🔊 Speaking response...")
        speak_text(response)

def save_audio():
    """Save audio frames to WAV file"""
    global audio_frames
    
    print(f"   Saving {len(audio_frames)} audio chunks...")
    
    # Save to current directory instead of /tmp to avoid path issues
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_file = f"./recording_{timestamp}.wav"
    
    wf = wave.open(temp_file, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
    wf.setframerate(16000)
    wf.writeframes(b''.join(audio_frames))
    wf.close()
    
    file_size = os.path.getsize(temp_file)
    print(f"   Saved to: {temp_file} ({file_size} bytes)")
    
    return temp_file

def transcribe_audio(audio_file):
    """Transcribe audio using Whisper CLI"""
    txt_file = None
    try:
        # Check audio file
        file_size = os.path.getsize(audio_file)
        print(f"   Audio file: {audio_file}")
        print(f"   File size: {file_size} bytes")
        
        if file_size < 1000:
            print("   ⚠️  Audio file too small, probably silent")
            return None
        
        model = CONFIG.get("whisperModel", "base")
        language = CONFIG.get("language", "uk")
        
        # Map language codes
        whisper_lang = "uk" if language == "uk" else "en"
        
        print(f"   Using Whisper model: {model}, language: {whisper_lang}")
        
        # Check if whisper is available
        whisper_check = subprocess.run(["which", "whisper"], capture_output=True, text=True)
        if whisper_check.returncode != 0:
            print("   ❌ Whisper CLI not found! Run: pip install openai-whisper")
            return None
        
        print(f"   Whisper binary: {whisper_check.stdout.strip()}")
        
        # Run whisper
        cmd = ["whisper", audio_file, "--model", model, "--output_format", "txt", "--language", whisper_lang]
        print(f"   Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Debug output
        print(f"   Whisper return code: {result.returncode}")
        if result.stdout:
            print(f"   Whisper stdout: {result.stdout[:200]}")
        if result.stderr:
            print(f"   Whisper stderr: {result.stderr[:200]}")
        
        # Whisper writes output to <audio_file>.txt
        txt_file = audio_file.replace(".wav", ".txt")
        print(f"   Looking for output: {txt_file}")
        
        if os.path.exists(txt_file):
            with open(txt_file) as f:
                text = f.read().strip()
            
            if text:
                print(f"   ✅ Transcribed: {len(text)} characters")
                print(f"   Text: {text[:100]}")
            else:
                print("   ⚠️  Output file is empty")
            
            return text
        else:
            print(f"   ❌ Output file not found: {txt_file}")
            # List files in directory
            import glob
            similar = glob.glob(audio_file.replace(".wav", ".*"))
            print(f"   Files with same name: {similar}")
        
        return None
    except subprocess.TimeoutExpired:
        print("   ❌ Whisper timeout (60s)")
        return None
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Clean up files
        if txt_file and os.path.exists(txt_file):
            os.remove(txt_file)
        if audio_file and os.path.exists(audio_file):
            os.remove(audio_file)

def send_to_openclaw(text):
    """Send message to OpenClaw via WebSocket and get response"""
    try:
        print(f"   Sending via OpenClaw WebSocket...")
        
        # Get gateway config
        gateway_url = CONFIG.get("gatewayUrl", "ws://127.0.0.1:18789")
        gateway_token = CONFIG.get("gatewayToken")  # Optional
        telegram_user_id = CONFIG.get("telegramUserId")
        
        print(f"   Connecting to {gateway_url}...")
        
        # Run async WebSocket communication
        response_text = asyncio.run(_send_via_websocket(
            gateway_url, 
            gateway_token, 
            text, 
            telegram_user_id
        ))
        
        if response_text:
            print(f"   ✅ Got response ({len(response_text)} chars)")
            return response_text
        else:
            print(f"   ⚠️  No response received")
            return None
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def _send_via_websocket(gateway_url: str, token: str, message: str, to: str = None):
    """Async helper for WebSocket communication"""
    client = OpenClawClient(gateway_url, token)
    
    try:
        # Connect to gateway
        if not await client.connect():
            return None
        
        # Send message and get response
        response = await client.send_message(message, to=to, channel="telegram")
        
        return response
        
    finally:
        await client.disconnect()

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
        # Start recording when Space pressed while holding Cmd+Shift
        if key == keyboard.Key.space:
            if 'cmd' in current_modifiers and 'shift' in current_modifiers:
                if not is_recording:
                    print("🎤 Hotkey detected: Cmd+Shift+Space")
                    print("   Hold the keys to record, release to stop")
                    start_recording()
    except AttributeError:
        pass

def on_release(key):
    """Handle key release"""
    try:
        # Remove released modifiers from tracking
        if key == keyboard.Key.cmd or key == keyboard.Key.cmd_r:
            current_modifiers.discard('cmd')
        elif key == keyboard.Key.shift or key == keyboard.Key.shift_r:
            current_modifiers.discard('shift')
        
        # Stop recording when ANY of the hotkey keys is released
        # (Space, Cmd, or Shift)
        if is_recording:
            if (key == keyboard.Key.space or 
                key == keyboard.Key.cmd or key == keyboard.Key.cmd_r or
                key == keyboard.Key.shift or key == keyboard.Key.shift_r):
                print("   Released hotkey, stopping recording...")
                stop_recording()
        
        # Exit on Escape
        if key == keyboard.Key.esc:
            print("\n👋 Exiting...")
            return False
    except AttributeError:
        pass

def list_audio_devices():
    """List available audio input devices"""
    print("🎤 Audio input devices:")
    p = pyaudio.PyAudio()
    
    devices = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            devices.append((i, info))
            marker = ""
            
            # Check if this is the configured device
            configured_device = CONFIG.get("inputDevice")
            if configured_device is not None and i == configured_device:
                marker = " ← CONFIGURED"
            
            print(f"   [{i}] {info['name']}{marker}")
    
    default_input = p.get_default_input_device_info()
    default_index = default_input['index']
    print(f"   System Default: [{default_index}] {default_input['name']}")
    
    # Show which one will be used
    configured_device = CONFIG.get("inputDevice")
    if configured_device is not None:
        if configured_device < len(devices):
            used_device = devices[configured_device][1]
            print(f"   ✅ Will use: [{configured_device}] {used_device['name']}")
        else:
            print(f"   ⚠️  Configured device [{configured_device}] not found, using default")
            print(f"   ✅ Will use: [{default_index}] {default_input['name']}")
    else:
        print(f"   ✅ Will use default: [{default_index}] {default_input['name']}")
    
    p.terminate()
    print()

def main():
    """Main entry point"""
    print("🎙️  OpenClaw Voice Hotkey Assistant")
    print(f"🔑 Hotkey: {CONFIG['hotkey']} (Push-to-talk)")
    print()
    
    # List audio devices
    try:
        list_audio_devices()
    except Exception as e:
        print(f"⚠️  Could not list audio devices: {e}")
        print()
    
    print("💡 Usage:")
    print("   1. Press and HOLD Cmd+Shift+Space")
    print("   2. Speak while holding")
    print("   3. Release any key to stop recording")
    print("   4. Press Escape to exit")
    print()
    print("⚠️  Make sure Accessibility permissions are granted!")
    print("   System Settings → Privacy & Security → Accessibility → Terminal")
    print()
    
    # Start listening for hotkeys
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

if __name__ == "__main__":
    main()
