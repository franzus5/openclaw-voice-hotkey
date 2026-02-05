# OpenClaw Voice Hotkey

Voice assistant for OpenClaw - press a hotkey, speak, get AI response.

## Features

- 🎤 **Global hotkey** (`Cmd+Shift+Space`) to start voice recording
- 🗣️ **Local Whisper transcription** (no API calls, free)
- 🤖 **OpenClaw integration** - sends transcription to your local OpenClaw instance
- 🔊 **Audio response** - speaks the answer back using TTS

## How it works

1. Press `Cmd+Shift+Space` → recording starts
2. Speak your question
3. Release hotkey → recording stops, Whisper transcribes locally
4. Text sent to OpenClaw gateway (`ws://127.0.0.1:18789`)
5. OpenClaw responds
6. Response is spoken aloud via TTS (`say` or `sag`)

## Requirements

- macOS 12.0+
- Python 3.9+
- OpenClaw running locally
- Whisper CLI (`brew install whisper`)
- (Optional) `sag` for better TTS quality

## Installation

```bash
# Clone the repo
git clone https://github.com/franzus5/openclaw-voice-hotkey.git
cd openclaw-voice-hotkey

# Install Python dependencies
pip3 install -r requirements.txt

# Run the assistant
python3 voice_hotkey.py
```

## Configuration

Edit `config.json`:

```json
{
  "hotkey": "cmd+shift+space",
  "openclawGateway": "ws://127.0.0.1:18789",
  "whisperModel": "base",
  "ttsEngine": "say"
}
```

## Usage

1. Start the assistant: `python3 voice_hotkey.py`
2. Press and hold `Cmd+Shift+Space`
3. Speak your question
4. Release the hotkey
5. Wait for transcription + AI response

## Architecture

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
│     TTS     │  say/sag response
└─────────────┘
```

## Roadmap

- [x] Create repo structure
- [ ] Implement hotkey listener (pynput)
- [ ] Implement audio recording (pyaudio)
- [ ] Whisper CLI integration
- [ ] OpenClaw WebSocket client
- [ ] TTS playback
- [ ] Config file support
- [ ] Menu bar app (optional)

## License

MIT
