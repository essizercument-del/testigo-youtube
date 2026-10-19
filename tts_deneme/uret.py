import asyncio, json, time
import edge_tts
lines = [l.strip() for l in open("tts_deneme/metin.txt", encoding="utf-8") if l.strip()]
async def one(text, voice, rate, out):
    c = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words = []
    with open(out + ".mp3", "wb") as f:
        async for ch in c.stream():
            if ch["type"] == "audio": f.write(ch["data"])
            elif ch["type"] == "WordBoundary": words.append({"t": ch["offset"]/1e7, "d": ch["duration"]/1e7, "w": ch["text"]})
    json.dump(words, open(out + ".json", "w", encoding="utf-8"), ensure_ascii=False)
for voice, tag in [("tr-TR-AhmetNeural", "ahmet"), ("tr-TR-EmelNeural", "emel")]:
    for i, t in enumerate(lines, 1):
        for deneme in range(5):
            try:
                asyncio.run(one(t, voice, "+8%", f"cikti/{tag}_{i:02d}")); print("OK", tag, i); break
            except Exception as e:
                print("HATA", tag, i, deneme, repr(e)); time.sleep(3 + deneme * 3)
