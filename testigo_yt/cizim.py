"""Çizim yardımcıları: font, renk, yazı kaydırma, animasyon eğrileri, arka planlar."""
from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

KOK = Path(__file__).resolve().parent.parent
FONT = KOK / "assets" / "fonts"

# ---- renkler ---------------------------------------------------------------
ZEMIN = (11, 15, 20)
PANEL = (22, 28, 37)
PANEL_KENAR = (40, 49, 62)
YAZI = (242, 244, 247)
SOLUK = (154, 164, 178)
VURGU = (255, 194, 26)        # Testigo amber (elektrik)
CUBUK = (70, 82, 99)          # vurgusuz çubuk
DUSUK = (126, 226, 184)       # düşük kademe değeri
YUKSEK = (255, 138, 101)      # yüksek kademe değeri

# Shorts arayüzü alt ve sağ kenarı kapatıyor; önemli içerik bu bandın içinde kalır.
GUVENLI_UST = 230
GUVENLI_ALT = 1500
KENAR = 84


@lru_cache(maxsize=64)
def font(ad: str, boyut: int) -> ImageFont.FreeTypeFont:
    dosya = {
        "siyah": "InterDisplay-Black.otf",
        "kalin": "InterDisplay-Bold.otf",
        "yari": "Inter-SemiBold.otf",
        "orta": "Inter-Medium.otf",
    }[ad]
    return ImageFont.truetype(str(FONT / dosya), boyut)


# ---- animasyon -------------------------------------------------------------
def kis(x: float) -> float:
    return max(0.0, min(1.0, x))


def yumusak(x: float) -> float:
    """ease-out cubic"""
    x = kis(x)
    return 1 - (1 - x) ** 3


def ilerleme(t: float, bas: float, sure: float) -> float:
    return kis((t - bas) / sure) if sure > 0 else float(t >= bas)


def renk_a(renk: tuple, a: float) -> tuple:
    return (*renk[:3], int(255 * kis(a)))


# ---- yazı ------------------------------------------------------------------
def genislik(f: ImageFont.FreeTypeFont, metin: str) -> int:
    return int(f.getlength(metin))


def kaydir(metin: str, f: ImageFont.FreeTypeFont, max_g: int) -> list[str]:
    satirlar: list[str] = []
    for paragraf in metin.split("\n"):
        kelimeler, satir = paragraf.split(), ""
        for k in kelimeler:
            dene = f"{satir} {k}".strip()
            if genislik(f, dene) <= max_g or not satir:
                satir = dene
            else:
                satirlar.append(satir)
                satir = k
        satirlar.append(satir)
    return satirlar


def sigdir(metin: str, ad: str, boyut: int, max_g: int, max_satir: int, en_kucuk: int = 40):
    """Metni max_satir'a sığana kadar fontu küçültür."""
    while True:
        f = font(ad, boyut)
        satirlar = kaydir(metin, f, max_g)
        if len(satirlar) <= max_satir and all(genislik(f, s) <= max_g for s in satirlar):
            return f, satirlar
        if boyut <= en_kucuk:
            return f, satirlar
        boyut -= 4


def yazi_blok(d: ImageDraw.ImageDraw, satirlar: list[str], f, y: int, renk, a: float = 1.0,
              hiza: str = "orta", x: int | None = None, W: int = 1080, aralik: float = 1.12,
              kayma: float = 0.0) -> int:
    """Satırları çizer, bloğun altındaki y'yi döndürür. kayma: yukarı kayarak gelme (px)."""
    yuk = int(f.size * aralik)
    for i, s in enumerate(satirlar):
        g = genislik(f, s)
        if hiza == "orta":
            sx = (W - g) // 2
        elif hiza == "sol":
            sx = x if x is not None else KENAR
        else:
            sx = (x if x is not None else W - KENAR) - g
        d.text((sx, y + i * yuk + kayma), s, font=f, fill=renk_a(renk, a))
    return y + len(satirlar) * yuk


def hap(d: ImageDraw.ImageDraw, merkez_x: int, y: int, metin: str, f, zemin, yazi, a: float = 1.0,
        pad_x: int = 30, pad_y: int = 16) -> tuple[int, int]:
    g = genislik(f, metin)
    asc, desc = f.getmetrics()
    h = asc + desc
    x0 = merkez_x - g // 2 - pad_x
    d.rounded_rectangle((x0, y, x0 + g + 2 * pad_x, y + h + 2 * pad_y), radius=(h + 2 * pad_y) // 2,
                        fill=renk_a(zemin, a))
    d.text((x0 + pad_x, y + pad_y), metin, font=f, fill=renk_a(yazi, a))
    return x0 + g + 2 * pad_x, y + h + 2 * pad_y


def simsek(d: ImageDraw.ImageDraw, x: int, y: int, boy: int, renk, a: float = 1.0):
    """Küçük şimşek simgesi (sol üst köşe x,y)."""
    s = boy / 100
    noktalar = [(58, 0), (8, 58), (44, 58), (34, 100), (92, 38), (54, 38), (66, 0)]
    d.polygon([(x + px * s, y + py * s) for px, py in noktalar], fill=renk_a(renk, a))


# ---- arka planlar ----------------------------------------------------------
def duz_zemin(W: int, H: int) -> Image.Image:
    """Koyu zemin + üstte hafif amber ışıma + çok soluk ızgara."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W * 0.5) / (W * 0.9)) ** 2 + ((yy - H * 0.12) / (H * 0.45)) ** 2)
    isik = np.clip(1 - r, 0, 1) ** 2 * 0.22
    taban = np.array(ZEMIN, np.float32)
    v = np.array(VURGU, np.float32)
    img = taban[None, None, :] * (1 - isik[..., None]) + v[None, None, :] * isik[..., None] * 0.55
    izgara = ((xx.astype(int) % 72 == 0) | (yy.astype(int) % 72 == 0)).astype(np.float32) * 6
    img = img + izgara[..., None]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def karartma_maskesi(W: int, H: int) -> Image.Image:
    """Fotoğraf/klip üstüne: genel karartma + alta doğru koyulaşan geçiş (RGBA)."""
    y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
    a = 0.45 + 0.5 * np.clip((y - 0.25) / 0.6, 0, 1)
    a = np.repeat(a, W, axis=1)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., :3] = ZEMIN
    rgba[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


class FotoZemin:
    """Fotoğrafı ekrana kaplar, yavaş yakınlaştırma (Ken Burns) uygular."""

    def __init__(self, yol: Path, W: int, H: int, maske: Image.Image, yon: int = 1):
        self.W, self.H, self.maske, self.yon = W, H, maske, yon
        img = ImageOps.exif_transpose(Image.open(yol)).convert("RGB")
        self.kaynak = ImageOps.fit(img, (int(W * 1.18), int(H * 1.18)), Image.LANCZOS)

    def kare(self, p: float) -> Image.Image:
        z = 1.18 - 0.14 * (p if self.yon > 0 else 1 - p)
        kw, kh = int(self.W * z), int(self.H * z)
        sw, sh = self.kaynak.size
        x0, y0 = (sw - kw) // 2, int((sh - kh) * 0.4)
        k = self.kaynak.crop((x0, y0, x0 + kw, y0 + kh)).resize((self.W, self.H), Image.BILINEAR)
        k.paste(self.maske, (0, 0), self.maske)
        return k


class KlipZemin:
    """Videoyu ffmpeg ile kare kare okur (dikeye kırpılmış), bitince başa sarar."""

    def __init__(self, yol: Path, W: int, H: int, fps: int, maske: Image.Image):
        self.yol, self.W, self.H, self.fps, self.maske = yol, W, H, fps, maske
        self.proc = None
        self._ac()

    def _ac(self):
        if self.proc:
            self.proc.kill()
        vf = (f"scale={self.W}:{self.H}:force_original_aspect_ratio=increase,"
              f"crop={self.W}:{self.H},fps={self.fps}")
        self.proc = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-i", str(self.yol), "-vf", vf, "-an",
             "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE)

    def kare(self, p: float) -> Image.Image:
        n = self.W * self.H * 3
        veri = self.proc.stdout.read(n)
        if len(veri) < n:
            self._ac()
            veri = self.proc.stdout.read(n)
        k = Image.frombytes("RGB", (self.W, self.H), veri)
        k.paste(self.maske, (0, 0), self.maske)
        return k

    def kapat(self):
        if self.proc:
            self.proc.kill()
            self.proc = None
