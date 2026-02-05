#!/bin/bash
set -e

echo "🚀 OpenClaw Voice Hotkey - Local Setup (self-contained)"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install it first: brew install python3"
    exit 1
fi

echo "✓ Python 3 found"

# Check/Install Homebrew dependencies (these MUST be system-wide)
echo ""
echo "📦 Installing system dependencies (portaudio, ffmpeg)..."

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

# Create local virtual environment
echo ""
echo "🐍 Creating local Python environment (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✓ venv created"
else
    echo "  ✓ venv already exists"
fi

# Activate venv and install dependencies
echo ""
echo "📥 Installing Python packages locally..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Install Whisper with local model cache
echo ""
echo "🎤 Installing Whisper..."
pip install --upgrade openai-whisper

# Download Whisper model to local directory
echo ""
echo "📥 Downloading Whisper model locally (base - 74MB)..."
mkdir -p ./models/whisper
export XDG_CACHE_HOME="$(pwd)/models/whisper"
python3 << 'PYEOF'
import os
import whisper

# Set local cache
os.environ['XDG_CACHE_HOME'] = os.path.join(os.getcwd(), 'models', 'whisper')

# Download model
print("  Downloading base model...")
whisper.load_model('base', download_root=os.path.join(os.getcwd(), 'models', 'whisper'))
print("  ✓ Model downloaded to ./models/whisper/")
PYEOF

# Optional: Install Piper for better TTS
echo ""
read -p "Install Piper TTS for better voice quality? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📢 Installing Piper TTS locally..."
    
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
    python3 - <<'EOF'
import json
with open('config.json', 'r') as f:
    config = json.load(f)
config['ttsEngine'] = 'piper'
config['piperBinary'] = './bin/piper'
config['piperModelUK'] = './models/tts/uk_UA-lada-x_low.onnx'
config['piperModelEN'] = './models/tts/en_US-lessac-medium.onnx'
config['piperModel'] = './models/tts/uk_UA-lada-x_low.onnx'
config['language'] = 'uk'
with open('config.json', 'w') as f:
    json.dump(config, f, indent=2)
print("  ✓ Config updated to use Piper with Ukrainian voice")
EOF
fi

deactivate

# Create activation script
cat > activate.sh << 'ACTEOF'
#!/bin/bash
# Activate local environment
source venv/bin/activate
export XDG_CACHE_HOME="$(pwd)/models/whisper"
export PYTHONPATH="$(pwd):$PYTHONPATH"
echo "✓ Local environment activated"
echo "  Python: $(which python3)"
echo "  Whisper models: ./models/whisper/"
echo ""
echo "To run the assistant: python3 voice_hotkey.py"
echo "To deactivate: deactivate"
ACTEOF
chmod +x activate.sh

echo ""
echo "✅ Local setup complete!"
echo ""
echo "📦 Everything is now local in this project:"
echo "  ./venv/               ← Python packages"
echo "  ./models/whisper/     ← Whisper models"
echo "  ./models/tts/         ← TTS voice models"
echo "  ./bin/                ← Piper binary"
echo ""
echo "To use the assistant:"
echo "  source activate.sh    # Activate local environment"
echo "  python3 voice_hotkey.py"
echo ""
echo "Or use the run script:"
echo "  ./run.sh"
echo ""
