import asyncio, json, sys
import edge_tts
async def main(voice, rate, out):
    text = open("tts_deneme/metin.txt", encoding="utf-8").read().strip()
    c = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(out + ".mp3", "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                words.append({"t": ch["offset"] / 1e7, "d": ch["duration"] / 1e7, "w": ch["text"]})
    json.dump(words, open(out + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
import traceback
import subprocess; subprocess.run(["edge-tts","--list-voices"],stdout=open("cikti/sesler.txt","w"))
import subprocess; subprocess.run(["edge-tts","--list-voices"],stdout=open("cikti/sesler.txt","w"))
print("edge-tts", getattr(edge_tts, "__version__", "?"))
for v, r, o in [("tr-TR-AhmetNeural", "+8%", "ahmet"), ("tr-TR-EmelNeural", "+8%", "emel")]:
    try:
        asyncio.run(main(v, r, "cikti/" + o)); print("OK", v)
    except Exception:
        traceback.print_exc()
