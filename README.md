# OpenClaw Voice Hotkey

Voice assistant for OpenClaw - press a hotkey, speak, get AI response.

## Features

- 🎤 **Global hotkey** (`Cmd+Shift+Space`) to start voice recording
- 🗣️ **Local Whisper transcription** (no API calls, free)
- 🤖 **OpenClaw integration** - sends transcription to your local OpenClaw instance
- 🔊 **Audio response** - speaks the answer back using TTS
- 🇺🇦 **Ukrainian language support** - native Ukrainian TTS voice (Lada)

## How it works

1. Press and **hold** `Cmd+Shift+Space` → recording starts
2. Speak your question while holding
3. Release hotkey → recording stops, Whisper transcribes locally
4. Text sent to OpenClaw via CLI (`openclaw inject`)
5. OpenClaw response appears in your main chat (Telegram/etc)
6. *(Future: speak response aloud via TTS)*

## Requirements

- macOS 12.0+
- Python 3.9+
- OpenClaw running locally
- Homebrew (for dependencies)
- **Accessibility permissions** (for hotkey detection) - see [PERMISSIONS.md](PERMISSIONS.md)

## Installation

### Option 1: Local Setup (Recommended - like node_modules)

Everything installs **locally in the project** - no global pollution:

```bash
# Clone the repo
git clone https://github.com/franzus5/openclaw-voice-hotkey.git
cd openclaw-voice-hotkey

# Run local setup
chmod +x setup_local.sh
./setup_local.sh

# Run the assistant
./run.sh
```

This creates:
```
openclaw-voice-hotkey/
  ├── venv/              ← Python packages (local virtualenv)
  ├── models/
  │   ├── whisper/       ← Whisper models (~74MB)
  │   └── tts/           ← TTS voice models
  └── bin/               ← Piper binary
```

**No global installation!** Everything is self-contained.

### Option 2: Global Setup (Traditional)

```bash
# Clone the repo
git clone https://github.com/franzus5/openclaw-voice-hotkey.git
cd openclaw-voice-hotkey

# Run global setup
chmod +x setup.sh
./setup.sh

# Run the assistant
python3 voice_hotkey.py
```

This installs:
- Python packages globally
- Whisper models in `~/.cache/whisper/`
- Piper TTS locally in project

### Manual Installation

If you prefer manual setup:

```bash
# Install system dependencies
brew install portaudio ffmpeg

# Create venv
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt

# Run
python3 voice_hotkey.py
```

## Configuration

Edit `config.json`:

```json
{
  "hotkey": "cmd+shift+space",
  "whisperModel": "base",
  "ttsEngine": "piper",
  "language": "uk",
  "inputDevice": null,
  "openclawBinary": "/Users/YOUR_USERNAME/.nvm/versions/node/v24.13.0/bin/openclaw",
  "piperBinary": "./bin/piper",
  "piperModelUK": "./models/tts/uk_UA-lada-x_low.onnx",
  "piperModelEN": "./models/tts/en_US-lessac-medium.onnx",
  "piperModel": "./models/tts/uk_UA-lada-x_low.onnx"
}
```

**Options:**

- `hotkey`: Keyboard shortcut (default: `cmd+shift+space`)
- `whisperModel`: Whisper model size (`tiny`, `base`, `small`, `medium`, `large`)
  - `tiny`: fastest, lowest quality (~39MB)
  - `base`: good balance (~74MB) - **recommended**
  - `small`: better quality (~244MB)
  - `medium`: high quality (~769MB)
  - `large`: best quality (~1.5GB)
- `ttsEngine`: Text-to-speech engine
  - `say`: macOS built-in (fast, decent quality)
  - `piper`: Local TTS (better quality, more natural, **supports Ukrainian**)
  - `sag`: ElevenLabs via skill (requires API key, cloud-based)
- `language`: Language for Piper TTS (`uk` or `en`)
  - `uk`: Ukrainian voice (Lada) - **default**
  - `en`: English voice (Lessac)
- `inputDevice`: Audio input device index (see device list on startup)
  - `null`: use system default
  - `2`: use device #2 (e.g., headset microphone)
  - Check device list when starting the assistant
- `openclawBinary`: Full path to OpenClaw CLI (auto-detected if not set)
  - Example: `~/.nvm/versions/node/v24.13.0/bin/openclaw`
  - If OpenClaw is not in PATH, set this explicitly
- `piperModelUK`: Path to Ukrainian voice model
- `piperModelEN`: Path to English voice model

## Usage

1. Start the assistant: `python3 voice_hotkey.py`
2. Press and hold `Cmd+Shift+Space`
3. Speak your question
4. Release the hotkey
5. Wait for transcription + AI response

## Architecture

### Data Flow

```
┌─────────────┐
│   Hotkey    │  Cmd+Shift+Space
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Record    │  pyaudio → audio.wav
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Whisper   │  whisper audio.wav → text
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  OpenClaw   │  ws://127.0.0.1:18789
│   Gateway   │  send(text) → response
└──────┬──────┘
       │
       ▼
┌─────────────┐
│     TTS     │  piper/say → speech
└─────────────┘
```

### Project Structure

```
openclaw-voice-hotkey/
├── voice_hotkey.py       # Main application
├── config.json           # Configuration
├── requirements.txt      # Python dependencies
├── setup_local.sh        # Local setup (recommended)
├── setup.sh              # Global setup
├── run.sh                # Run with local env
├── test_components.py    # Component tests
│
├── venv/                 # Python virtualenv (local)
│   └── lib/              # Python packages
│
├── models/               # AI models (local)
│   ├── whisper/          # Speech recognition
│   │   └── base.pt       # ~74MB
│   └── tts/              # Text-to-speech
│       ├── uk_UA-lada-x_low.onnx      # Ukrainian
│       └── en_US-lessac-medium.onnx   # English
│
└── bin/                  # Binaries (local)
    └── piper             # TTS engine
```

## Troubleshooting

### "This process is not trusted!" error

You need to grant **Accessibility** permissions to Terminal.

👉 **See [PERMISSIONS.md](PERMISSIONS.md) for detailed instructions**

Quick fix:
1. System Settings → Privacy & Security → Accessibility
2. Add Terminal.app
3. Restart the assistant

### Hotkey not working

1. Check Accessibility permissions (see above)
2. Make sure you press **Cmd+Shift+Space** (all three keys)
3. Try restarting Terminal completely

### "No speech detected"

1. Check microphone permissions (System Settings → Privacy & Security → Microphone)
2. Speak clearly and hold hotkey while speaking
3. Recording duration must be > 0.5 seconds
4. Try testing microphone: `rec test.wav trim 0 3 && play test.wav`

### Message not appearing in OpenClaw

1. Make sure OpenClaw is running: `openclaw status`
2. Check you're in the main session (Telegram/etc)
3. Message is sent via `openclaw inject` command

## Roadmap

- [x] Create repo structure
- [x] Implement hotkey listener (pynput)
- [x] Implement audio recording (pyaudio)
- [x] Whisper CLI integration
- [x] Local TTS (Piper) with Ukrainian support
- [x] Self-contained setup (like node_modules)
- [ ] OpenClaw WebSocket client (in progress)
- [ ] Proper Cmd+Shift+Space detection (done, needs testing)
- [ ] Menu bar app (optional)
- [ ] Standalone .app bundle (no Terminal required)

## License

MIT
