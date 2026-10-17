"""Arka plan müziği: assets/muzik içinde mp3/m4a/wav varsa ondan seçer,
yoksa yumuşak bir ambiyans altlığını kendisi üretir (telif sorunu olmaz)."""
from __future__ import annotations

import random
import wave
import zlib
from pathlib import Path

import numpy as np

KOK = Path(__file__).resolve().parent.parent
MUZIK = KOK / "assets" / "muzik"
SR = 44100


def muzik_sec(tohum: str) -> Path | None:
    if not MUZIK.is_dir():
        return None
    dosyalar = sorted(p for p in MUZIK.iterdir() if p.suffix.lower() in {".mp3", ".m4a", ".wav", ".ogg"})
    if not dosyalar:
        return None
    return random.Random(tohum).choice(dosyalar)


def _nota(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def ambiyans_uret(sure: float, hedef: Path, tohum: str) -> Path:
    """Am - F - C - G üzerinde yumuşak pad + hafif nabız. Basit, nötr, telifsiz."""
    rng = np.random.default_rng(zlib.crc32(tohum.encode()))
    n = int(sure * SR)
    t = np.arange(n) / SR
    akorlar = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
    kaydir = int(rng.integers(0, 4))
    akorlar = akorlar[kaydir:] + akorlar[:kaydir]
    olcu = 2.4  # saniye / akor
    ses = np.zeros(n)
    for i in range(int(np.ceil(sure / olcu)) + 1):
        bas = i * olcu
        akor = akorlar[i % 4]
        s0, s1 = int(bas * SR), min(n, int((bas + olcu + 0.8) * SR))
        if s0 >= n:
            break
        tt = t[s0:s1] - bas
        zarf = np.clip(tt / (0.05 if i == 0 else 0.9), 0, 1) * np.clip((olcu + 0.8 - tt) / 0.8, 0, 1)
        for m in akor + [akor[0] - 12]:
            f = _nota(m)
            dalga = np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 2 * f * tt + 0.3)
            ses[s0:s1] += dalga * zarf * (0.6 if m < akor[0] else 0.35)
        # hafif arpej nabzı
        for j in range(8):
            ps = bas + j * olcu / 8
            p0 = int(ps * SR)
            if p0 >= n:
                break
            p1 = min(n, p0 + int(0.28 * SR))
            pt = t[p0:p1] - ps
            m = akor[j % 3] + 12
            ses[p0:p1] += np.sin(2 * np.pi * _nota(m) * pt) * np.exp(-pt * 9) * 0.22
    # yumuşak eko
    gecikme = int(0.3 * SR)
    eko = np.zeros(n)
    eko[gecikme:] = ses[:-gecikme] * 0.3
    ses = ses + eko
    # giriş/çıkış
    gir, cik = int(0.05 * SR), int(1.5 * SR)  # müzik ilk karede başlar
    ses[:gir] *= np.linspace(0, 1, gir)
    ses[-cik:] *= np.linspace(1, 0, cik)
    ses = ses / (np.max(np.abs(ses)) + 1e-9) * 0.8
    stereo = np.stack([ses, np.roll(ses, 220)], axis=1)
    veri = (stereo * 32767).astype(np.int16)
    with wave.open(str(hedef), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(veri.tobytes())
    return hedef
