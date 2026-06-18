import pyaudio


def resolve_input_index(value: str | int) -> int:
    if isinstance(value, int):
        return value
    if value and str(value).strip().lower() != "auto":
        return int(value)

    audio = pyaudio.PyAudio()
    try:
        candidates = []
        for index in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(index)
            if info.get("maxInputChannels", 0) <= 0:
                continue
            name = str(info.get("name", ""))
            if "respeaker" in name.lower() or "xvf3800" in name.lower():
                candidates.append((index, name))
        if candidates:
            index, name = candidates[0]
            print(f"[Audio] Auto-selected input device [{index}] {name}")
            return index

        for index in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(index)
            if info.get("maxInputChannels", 0) > 0:
                name = info.get("name", "")
                print(f"[Audio] Auto-selected fallback input device [{index}] {name}")
                return index
    finally:
        audio.terminate()

    raise RuntimeError("No audio input device found")
