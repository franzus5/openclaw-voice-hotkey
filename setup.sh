#!/bin/bash
set -e

echo "🚀 OpenClaw Voice Hotkey Setup"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install it first: brew install python3"
    exit 1
fi

echo "✓ Python 3 found"

# Check/Install Homebrew dependencies
echo ""
echo "📦 Installing system dependencies..."

if ! command -v brew &> /dev/null; then
    echo "❌ Homebrew not found. Install from https://brew.sh"
    exit 1
fi

# Install portaudio (required for pyaudio)
if ! brew list portaudio &> /dev/null; then
    echo "  Installing portaudio..."
    brew install portaudio
else
    echo "  ✓ portaudio already installed"
fi

# Install ffmpeg (for audio processing)
if ! brew list ffmpeg &> /dev/null; then
    echo "  Installing ffmpeg..."
    brew install ffmpeg
else
    echo "  ✓ ffmpeg already installed"
fi

# Install OpenAI Whisper CLI
echo ""
echo "🎤 Installing Whisper for speech recognition..."
if ! command -v whisper &> /dev/null; then
    pip3 install --upgrade openai-whisper
    echo "  ✓ Whisper installed"
else
    echo "  ✓ Whisper already installed"
fi

# Download default Whisper model
echo ""
echo "📥 Downloading Whisper model (base - 74MB)..."
echo "  This will download the model on first run if not cached"
python3 -c "import whisper; whisper.load_model('base')" || echo "  Model will download on first use"

# Install Python dependencies
echo ""
echo "🐍 Installing Python dependencies..."
pip3 install -r requirements.txt

# Optional: Install Piper for better TTS
echo ""
read -p "Install Piper TTS for better voice quality? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📢 Installing Piper TTS..."
    
    # Download piper binary for macOS
    PIPER_VERSION="2023.11.14-2"
    PIPER_URL="https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/piper_macos_arm64.tar.gz"
    
    mkdir -p ./bin
    cd ./bin
    
    if [ ! -f "piper" ]; then
        echo "  Downloading piper..."
        curl -L "$PIPER_URL" -o piper.tar.gz
        tar -xzf piper.tar.gz
        rm piper.tar.gz
        chmod +x piper
        echo "  ✓ Piper installed to ./bin/piper"
    else
        echo "  ✓ Piper already installed"
    fi
    
    cd ..
    
    # Download voice models
    echo "  Downloading voice models..."
    mkdir -p ./models/tts
    cd ./models/tts
    
    # Ukrainian voice (Lada - medium quality)
    if [ ! -f "uk_UA-lada-x_low.onnx" ]; then
        echo "    Downloading Ukrainian voice (Lada)..."
        curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/lada/x_low/uk_UA-lada-x_low.onnx" -o uk_UA-lada-x_low.onnx
        curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/uk/uk_UA/lada/x_low/uk_UA-lada-x_low.onnx.json" -o uk_UA-lada-x_low.onnx.json
        echo "    ✓ Ukrainian voice downloaded"
    else
        echo "    ✓ Ukrainian voice already exists"
    fi
    
    # English voice (Lessac - medium quality)
    if [ ! -f "en_US-lessac-medium.onnx" ]; then
        echo "    Downloading English voice (Lessac)..."
        curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" -o en_US-lessac-medium.onnx
        curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" -o en_US-lessac-medium.onnx.json
        echo "    ✓ English voice downloaded"
    else
        echo "    ✓ English voice already exists"
    fi
    
    cd ../..
    
    # Update config to use piper
    python3 - <<EOF
import json
with open('config.json', 'r') as f:
    config = json.load(f)
config['ttsEngine'] = 'piper'
config['piperBinary'] = './bin/piper'
config['piperModelUK'] = './models/tts/uk_UA-lada-x_low.onnx'
config['piperModelEN'] = './models/tts/en_US-lessac-medium.onnx'
config['piperModel'] = './models/tts/uk_UA-lada-x_low.onnx'  # Default to Ukrainian
config['language'] = 'uk'
with open('config.json', 'w') as f:
    json.dump(config, f, indent=2)
print("  ✓ Config updated to use Piper with Ukrainian voice")
EOF
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To run the assistant:"
echo "  python3 voice_hotkey.py"
echo ""
echo "Configuration:"
echo "  Edit config.json to customize hotkeys, models, etc."
echo ""
