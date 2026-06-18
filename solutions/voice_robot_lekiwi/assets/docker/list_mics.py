"""list_mics.py — Run this first to find the correct MIC_INDEX for your Pi.
Usage: python list_mics.py
"""
import pyaudio

p = pyaudio.PyAudio()
print("\nAvailable audio INPUT devices:\n")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info["maxInputChannels"] > 0:
        print(f"  [{i}] {info['name']}  (rate={int(info['defaultSampleRate'])}Hz)")
p.terminate()
print("\nSet MIC_INDEX in config.env to the number in brackets.")
