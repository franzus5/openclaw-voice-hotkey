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
    """Send message to OpenClaw and get response"""
    try:
        print(f"   Sending via OpenClaw CLI...")
        
        # Path to openclaw binary (use configured or find it)
        openclaw_binary = CONFIG.get("openclawBinary")
        if not openclaw_binary:
            # Try to find it in common locations
            possible_paths = [
                os.path.expanduser("~/.nvm/versions/node/v24.13.0/bin/openclaw"),
                "/usr/local/bin/openclaw",
                "/opt/homebrew/bin/openclaw"
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    openclaw_binary = path
                    break
        
        if not openclaw_binary or not os.path.exists(openclaw_binary):
            print(f"   ❌ OpenClaw binary not found!")
            print(f"      Add 'openclawBinary' to config.json with full path")
            return None
        
        print(f"   Using: {openclaw_binary}")
        
        # Two-step approach:
        # 1. Get response without delivery (for TTS)
        # 2. Deliver to Telegram separately
        
        # Step 1: Get agent response
        cmd_get = [
            openclaw_binary, "agent",
            "--message", text,
            "--json"
        ]
        
        # Add user ID if configured (for session routing)
        telegram_user_id = CONFIG.get("telegramUserId")
        if telegram_user_id:
            cmd_get.extend(["--to", str(telegram_user_id)])
        
        print(f"   Getting agent response...")
        result = subprocess.run(
            cmd_get,
            capture_output=True,
            text=True,
            timeout=60  # Agent can take longer
        )
        
        if result.returncode != 0:
            print(f"   ⚠️  Agent error: {result.stderr}")
            return None
        
        # Parse JSON response
        response_text = None
        try:
            response_data = json.loads(result.stdout)
            response_text = response_data.get("reply", "")
            
            if not response_text:
                print(f"   ⚠️  Empty response from agent")
                return None
            
            print(f"   ✅ Got response ({len(response_text)} chars)")
            
        except json.JSONDecodeError as e:
            print(f"   ⚠️  Could not parse JSON response: {e}")
            print(f"   Raw output: {result.stdout[:200]}")
            return None
        
        # Step 2: Deliver to Telegram
        if telegram_user_id and response_text:
            print(f"   Delivering to Telegram...")
            cmd_deliver = [
                openclaw_binary, "message", "send",
                "--channel", "telegram",
                "--target", str(telegram_user_id),
                "--message", response_text
            ]
            
            deliver_result = subprocess.run(
                cmd_deliver,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if deliver_result.returncode == 0:
                print(f"   ✅ Delivered to Telegram")
            else:
                print(f"   ⚠️  Delivery warning: {deliver_result.stderr[:100]}")
        
        return response_text
        
    except subprocess.TimeoutExpired:
        print(f"   ❌ Agent timeout (60s)")
        return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
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
