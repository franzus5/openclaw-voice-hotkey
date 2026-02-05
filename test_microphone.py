#!/usr/bin/env python3
"""
Test microphone recording - saves a 3-second audio file
"""

import pyaudio
import wave
import time

print("🎤 Microphone Test")
print("=" * 50)
print()

# List devices
print("Available input devices:")
p = pyaudio.PyAudio()
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info['maxInputChannels'] > 0:
        print(f"  [{i}] {info['name']}")

default_input = p.get_default_input_device_info()
print(f"\nDefault input: {default_input['name']}")
print()

# Record 3 seconds
print("Recording 3 seconds...")
print("Speak now!")
print()

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 3

frames = []

stream = p.open(
    format=FORMAT,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)

for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)
    if i % 10 == 0:
        print(".", end="", flush=True)

print()
print("Recording complete!")

stream.stop_stream()
stream.close()
p.terminate()

# Save to file
OUTPUT_FILE = "test_recording.wav"
wf = wave.open(OUTPUT_FILE, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

import os
file_size = os.path.getsize(OUTPUT_FILE)

print()
print(f"✅ Saved to: {OUTPUT_FILE}")
print(f"   File size: {file_size} bytes")
print(f"   Duration: {RECORD_SECONDS}s")
print()
print("To play the recording:")
print(f"   afplay {OUTPUT_FILE}")
print()
print("If you hear your voice, microphone is working!")
print("If silent or no sound, check microphone permissions:")
print("   System Settings → Privacy & Security → Microphone → Terminal")
