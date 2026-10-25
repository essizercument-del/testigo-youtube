import json, subprocess, sys, numpy as np
B = "bolum5m"
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
import wave
raw = wave.open(f"tts_deneme/eleven/{B}_16k.wav").readframes(10**9)
audio = np.frombuffer(raw, np.int16).astype(np.float32)/32768
segs, info = m.transcribe(audio, language="tr", word_timestamps=True, beam_size=5)
out = []
for s in segs:
    for w in s.words: out.append({"t": round(w.start, 3), "e": round(w.end, 3), "w": w.word.strip()})
json.dump(out, open(f"tts_deneme/eleven/{B}_kelimeler.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(" ".join(f"{x['w']}@{x['t']}" for x in out))
