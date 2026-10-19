import json
from faster_whisper import WhisperModel
m = WhisperModel("small", device="cpu", compute_type="int8")
segs, info = m.transcribe("tts_deneme/eleven/bolum1.mp3", language="tr", word_timestamps=True, beam_size=5)
out = []
for s in segs:
    for w in s.words: out.append({"t": round(w.start, 3), "e": round(w.end, 3), "w": w.word.strip()})
json.dump(out, open("tts_deneme/eleven/bolum1_kelimeler.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(" ".join(f"{x['w']}@{x['t']}" for x in out))
