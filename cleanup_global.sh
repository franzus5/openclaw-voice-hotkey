#!/bin/bash
# Cleanup global installations after switching to local setup

echo "🧹 Cleaning up global Python packages..."
echo ""
echo "This will remove globally installed packages that are now in venv."
echo "Homebrew packages (portaudio, ffmpeg) will NOT be touched - they're needed."
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# List of packages to uninstall
PACKAGES=(
    "pynput"
    "pyaudio"
    "websockets"
    "openai-whisper"
    "torch"
    "numpy"
)

echo ""
echo "📦 Uninstalling global Python packages..."
for pkg in "${PACKAGES[@]}"; do
    if pip3 show "$pkg" &> /dev/null; then
        echo "  Removing $pkg..."
        pip3 uninstall -y "$pkg" 2>/dev/null || echo "    (skip - not installed or protected)"
    else
        echo "  ✓ $pkg not installed globally"
    fi
done

# Clean Whisper cache
echo ""
echo "💾 Checking Whisper cache..."
WHISPER_CACHE="$HOME/.cache/whisper"
if [ -d "$WHISPER_CACHE" ]; then
    CACHE_SIZE=$(du -sh "$WHISPER_CACHE" | cut -f1)
    echo "  Found Whisper cache: $CACHE_SIZE"
    read -p "  Delete Whisper cache? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$WHISPER_CACHE"
        echo "  ✓ Whisper cache deleted"
    else
        echo "  ✓ Whisper cache kept"
    fi
else
    echo "  ✓ No Whisper cache found"
fi

# Clean pip cache
echo ""
read -p "Clean pip cache? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip3 cache purge
    echo "  ✓ Pip cache cleared"
fi

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Kept (required by local setup):"
echo "  ✓ Homebrew (brew)"
echo "  ✓ portaudio (system library)"
echo "  ✓ ffmpeg (system binary)"
echo ""
echo "Local environment is in:"
echo "  ./venv/"
echo "  ./models/"
echo "  ./bin/"
echo ""
