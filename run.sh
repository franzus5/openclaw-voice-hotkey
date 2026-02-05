#!/bin/bash
# Run the voice assistant with local environment

# Activate local environment
if [ -f "activate.sh" ]; then
    source activate.sh
elif [ -d "venv" ]; then
    source venv/bin/activate
    export XDG_CACHE_HOME="$(pwd)/models/whisper"
else
    echo "❌ Local environment not found"
    echo "   Run ./setup_local.sh first"
    exit 1
fi

# Run the assistant
python3 voice_hotkey.py
