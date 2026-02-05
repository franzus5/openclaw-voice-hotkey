#!/usr/bin/env python3
"""
Test individual components of the voice assistant
"""

import sys
import subprocess
import json
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "config.json"
with open(CONFIG_FILE) as f:
    CONFIG = json.load(f)

def test_whisper():
    """Test Whisper installation"""
    print("🎤 Testing Whisper...")
    try:
        result = subprocess.run(
            ["whisper", "--help"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("  ✅ Whisper CLI is installed")
            return True
        else:
            print("  ❌ Whisper CLI not working")
            return False
    except FileNotFoundError:
        print("  ❌ Whisper CLI not found")
        print("     Run: pip3 install openai-whisper")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_tts():
    """Test TTS engine"""
    engine = CONFIG.get("ttsEngine", "say")
    print(f"📢 Testing TTS engine: {engine}...")
    
    try:
        if engine == "say":
            result = subprocess.run(
                ["say", "--help"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0 or result.returncode == 1:  # say returns 1 for --help
                print("  ✅ macOS 'say' command available")
                return True
        
        elif engine == "piper":
            piper_binary = CONFIG.get("piperBinary", "./bin/piper")
            if Path(piper_binary).exists():
                print(f"  ✅ Piper binary found: {piper_binary}")
                
                piper_model = CONFIG.get("piperModel", "./models/tts/en_US-lessac-medium.onnx")
                if Path(piper_model).exists():
                    print(f"  ✅ Piper model found: {piper_model}")
                    return True
                else:
                    print(f"  ❌ Piper model not found: {piper_model}")
                    print("     Run ./setup.sh and choose to install Piper")
                    return False
            else:
                print(f"  ❌ Piper binary not found: {piper_binary}")
                print("     Run ./setup.sh and choose to install Piper")
                return False
        
        elif engine == "sag":
            result = subprocess.run(
                ["sag", "--version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                print("  ✅ sag (ElevenLabs) command available")
                return True
            else:
                print("  ❌ sag command not found")
                print("     Install the sag skill in OpenClaw")
                return False
        
        print(f"  ❌ Unknown TTS engine: {engine}")
        return False
        
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_pyaudio():
    """Test PyAudio"""
    print("🎙️  Testing PyAudio...")
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        device_count = p.get_device_count()
        p.terminate()
        print(f"  ✅ PyAudio working ({device_count} audio devices found)")
        return True
    except ImportError:
        print("  ❌ PyAudio not installed")
        print("     Run: pip3 install pyaudio")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        print("     You may need: brew install portaudio")
        return False

def test_websockets():
    """Test WebSocket library"""
    print("🌐 Testing WebSocket library...")
    try:
        import websockets
        print("  ✅ websockets library installed")
        return True
    except ImportError:
        print("  ❌ websockets not installed")
        print("     Run: pip3 install websockets")
        return False

def test_pynput():
    """Test pynput"""
    print("⌨️  Testing pynput (hotkey library)...")
    try:
        from pynput import keyboard
        print("  ✅ pynput library installed")
        return True
    except ImportError:
        print("  ❌ pynput not installed")
        print("     Run: pip3 install pynput")
        return False

def main():
    print("🧪 OpenClaw Voice Hotkey - Component Tests\n")
    
    tests = [
        ("Whisper", test_whisper),
        ("TTS", test_tts),
        ("PyAudio", test_pyaudio),
        ("WebSockets", test_websockets),
        ("Pynput", test_pynput),
    ]
    
    results = []
    for name, test_func in tests:
        result = test_func()
        results.append((name, result))
        print()
    
    print("=" * 50)
    print("Summary:")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
        if not passed:
            all_passed = False
    
    print()
    
    if all_passed:
        print("🎉 All components working! Ready to run:")
        print("   python3 voice_hotkey.py")
    else:
        print("⚠️  Some components failed. Run ./setup.sh to fix issues.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
