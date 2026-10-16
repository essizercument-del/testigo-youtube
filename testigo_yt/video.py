"""Sahneleri kare kare çizip ffmpeg ile MP4'e çevirir, müziği ekler."""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from . import cizim as c
from .muzik import ambiyans_uret, muzik_sec
from .sahneler import H, W, Sahne, marka_basligi

GECIS = 0.3  # sahne sonu kararma süresi (sn)


def videoyu_uret(sahneler: list[Sahne], ayar: dict, cikis: Path, tohum: str,
                 onizleme_dir: Path | None = None) -> Path:
    fps = ayar["video"]["fps"]
    toplam = sum(s.sure for s in sahneler)
    kare_say = int(round(toplam * fps))
    duz = c.duz_zemin(W, H)
    cikis.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        sessiz = Path(tmp) / "goruntu.mp4"
        proc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
             "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(sessiz)],
            stdin=subprocess.PIPE)

        sinirlar, bas = [], 0.0
        for s in sahneler:
            sinirlar.append((bas, s))
            bas += s.sure

        try:
            for i in range(kare_say):
                t = i / fps
                for j, (b, s) in enumerate(sinirlar):
                    if t < b + s.sure or j == len(sinirlar) - 1:
                        break
                tl = t - b
                p = tl / s.sure
                kare = s.zemin.kare(p) if s.zemin else duz.copy()
                d = ImageDraw.Draw(kare, "RGBA")
                marka_basligi(d, ayar["kanal"]["marka"])
                s.ciz(kare, d, tl)
                son = j == len(sinirlar) - 1
                kalan = s.sure - tl
                if kalan < GECIS and not son:
                    kare = Image.blend(duz, kare, kalan / GECIS)
                if son and kalan < 0.5:
                    kare = Image.blend(Image.new("RGB", (W, H), c.ZEMIN), kare, kalan / 0.5)
                if onizleme_dir is not None and abs(tl - s.sure * 0.85) < 0.5 / fps:
                    onizleme_dir.mkdir(parents=True, exist_ok=True)
                    kare.save(onizleme_dir / f"{j + 1:02d}_{s.ad}.jpg", quality=88)
                proc.stdin.write(kare.tobytes())
        finally:
            proc.stdin.close()
            proc.wait()
            for s in sahneler:
                if hasattr(s.zemin, "kapat"):
                    s.zemin.kapat()
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg görüntü kodlaması başarısız")

        muzik = muzik_sec(tohum) or ambiyans_uret(toplam + 0.5, Path(tmp) / "muzik.wav", tohum)
        db = ayar["video"]["muzik_ses_db"]
        af = (f"volume={db}dB,afade=t=in:d=0.8,afade=t=out:st={max(0, toplam - 1.5):.2f}:d=1.5,"
              f"atrim=0:{toplam:.2f}")
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(sessiz), "-stream_loop", "-1",
             "-i", str(muzik), "-filter_complex", f"[1:a]{af}[a]", "-map", "0:v", "-map", "[a]",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart",
             str(cikis)],
            check=True)
    return cikis
