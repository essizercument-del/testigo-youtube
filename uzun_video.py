"""Uzun (16:9) derleme videosu: ölçülen ev aletleri en azdan en çoğa.

Kullanım (repo kök klasöründe):
  python uzun_video.py --metin      # seslendirme metnini yazar: out/uzun/seslendirme_metni.txt
  python uzun_video.py --kareler    # her sahneden bir JPG (hızlı kontrol, video üretmez)
  python uzun_video.py              # videoyu üretir: out/uzun/uzun_video.mp4 + kapak + açıklama

Seslendirme:
  Metindeki her bölümü ayrı ses dosyası olarak üret ve seslendirme/ klasörüne
  bölüm adıyla koy (örn. seslendirme/01_kanca.mp3, seslendirme/03_kettle.mp3).
  Ses dosyası olan sahnenin süresi sese göre ayarlanır, müzik kısılır.
  Ses yoksa süre metnin uzunluğundan tahmin edilir (önizleme için).

Ayarlar: data/uzun_video.json  ·  Cihaz verisi: data/olcumler.json  ·  Fotoğraflar: media/<id>/
"""
from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageOps

from testigo_yt import cizim as c
from testigo_yt import veri
from testigo_yt.muzik import ambiyans_uret, muzik_sec
from testigo_yt.veri import Cihaz, tr_sayi

W, H = 1920, 1080
KENAR = 96
SES_DIR = veri.KOK / "seslendirme"
CIKTI = veri.KOK / "out" / "uzun"
GECIS = 0.35
KELIME_SN = 2.3          # seslendirme hızı tahmini (kelime/sn), ses dosyası yokken
SES_PAY = 0.9            # ses bittikten sonra sahnede kalma (sn)
SEGMENT_RENK = [(92, 106, 126), (74, 86, 104), (110, 124, 145), (64, 75, 92), (100, 114, 134)]


# ---- veri ------------------------------------------------------------------
def ayarlar():
    ayar = veri.ayar_yukle()
    uz = json.loads((veri.KOK / "data" / "uzun_video.json").read_text(encoding="utf-8"))
    return ayar, uz


def cihazlar_hazirla(ayar, uz) -> list[Cihaz]:
    tum = veri.cihazlari_yukle(ayar)
    secili = []
    for x in tum:
        if x.id in uz.get("haric", []):
            continue
        hk = uz.get("haftalik_kullanim", {}).get(x.id)
        if hk and x.tip == "kullanim":
            x.ham = {**x.ham, "haftalik_kullanim": hk}
        if x.aylik_kwh:
            secili.append(x)
        else:
            print(f"! {x.kisa}: aylık tahmin için haftalik_kullanim yok, videoya alınmadı")
    return sorted(secili, key=lambda x: x.aylik_kwh)


def tl(x: Cihaz) -> float:
    return x.tl(x.aylik_kwh)[0]


def tam(x: float) -> str:
    return tr_sayi(x, 0)


# ---- seslendirme metni -----------------------------------------------------
def metinler(cihazlar: list[Cihaz], ayar, uz) -> dict[str, str]:
    n = len(cihazlar)
    t = ayar["tarife"]
    toplam = sum(tl(x) for x in cihazlar)
    en = cihazlar[-1]
    pay = tl(en) / toplam * 100
    m = {}
    m["01_kanca"] = (
        f"Evdeki {n} ev aletini prizden tek tek ölçtük. Sonuç gerçekten şaşırtıcı: bu {n} cihazın "
        f"aylık elektrik faturasının yüzde {tam(pay)}'i tek bir cihazdan geliyor. Hangisi olduğunu "
        f"sona saklıyoruz. En az yakandan en çok yakana doğru gidiyoruz.")
    m["02_yontem"] = (
        f"Önce nasıl ölçtüğümüzü anlatalım. Ölçümleri {uz.get('olcum_cihazi', 'enerji ölçer')} ile yaptık. "
        f"Buzdolabı, televizyon gibi uzun süre çalışan cihazları yaklaşık bir ay boyunca ölçerin üzerinde bıraktık. "
        f"Kurutma makinesi, su ısıtıcı gibi cihazlarda ise tek bir kullanımı ölçüp haftalık kullanıma göre aylığa çevirdik. "
        f"Hesapta kilovatsaat başına {tr_sayi(t['dusuk_kademe_tl'])} lira kullandık. Ayda "
        f"{t['kademe_siniri_kwh']} kilovatsaati aşan evlerde bu fiyat {tr_sayi(t['yuksek_kademe_tl'])} liraya çıkıyor.")
    kum = 0.0
    for i, x in enumerate(cihazlar):
        h = x.ham
        kum += tl(x)
        sira = n - i
        if i == n - 1:
            bas = f"Ve birinci sırada: {x.kisa}. "
        elif i == 0:
            bas = f"{sira}. sıradan başlıyoruz: {x.kisa.lower()}. "
        else:
            bas = f"{sira}. sırada {x.kisa.lower()} var. "
        if x.tip == "donem":
            kim = f"{x.ad} cihazını" if x.ad != x.kisa else "Bu cihazı"
            orta = (f"{kim} {h['gun']} gün boyunca prizden ölçtük. Toplam "
                    f"{tr_sayi(h['kwh'], 1)} kilovatsaat çıktı. Bu da ayda yaklaşık {tam(tl(x))} lira demek.")
        else:
            ka = h.get("kullanim_adi", "kullanım")
            orta = (f"{x.ad} için tek bir {ka} {tr_sayi(h['kwh'], 2)} kilovatsaat çekiyor; yani yaklaşık "
                    f"{tr_sayi(x.tl(h['kwh'])[0], 2)} lira. Haftada {h['haftalik_kullanim']} {ka} yaparsanız "
                    f"aylık maliyet yaklaşık {tam(tl(x))} lira.")
            if h.get("anlik_watt"):
                orta += f" Çalışırken anlık olarak {tam(h['anlik_watt'])} vat çekiyor."
        if i == n - 1:
            digerleri = toplam - tl(x)
            son = (f" Tek başına diğer {n - 1} cihazın toplamının {tr_sayi(tl(x) / digerleri, 1)} katı. "
                   f"{n} cihazın toplam faturası ayda yaklaşık {tam(toplam)} lira; bunun yüzde {tam(pay)}'i {x.kisa.lower()}.")
        elif i == 0:
            son = ""
        else:
            son = f" Şu ana kadarki toplam: ayda yaklaşık {tam(kum)} lira."
        m[f"{i + 3:02d}_{x.id}"] = bas + orta + son
    k = len(cihazlar) + 3
    sirali = list(reversed(cihazlar))
    liste = ", ".join(f"{x.kisa.lower()} {tam(tl(x))} lira" for x in sirali)
    m[f"{k:02d}_siralama"] = (
        f"Toparlayalım. Aylık maliyete göre sıralama şöyle: {liste}. "
        f"Faturayı düşürmek istiyorsanız ilk bakmanız gereken yer {en.kisa.lower()}.")
    m[f"{k + 1:02d}_kapanis"] = (
        "Siz bu cihazlardan hangisini en çok kullanıyorsunuz? Yorumlara yazın, kendi kullanımınıza göre "
        f"aylık maliyetini hesaplayalım. Tüm ölçümler ve elektrik hesaplama aracı {ayar['kanal']['site']} adresinde.")
    return m


# ---- çizim yardımcıları ----------------------------------------------------
def gir(t, bas, sure=0.5):
    p = c.yumusak(c.ilerleme(t, bas, sure))
    return p, (1 - p) * 40


def yazi(d, xy, metin, f, renk, a=1.0):
    d.text(xy, metin, font=f, fill=c.renk_a(renk, a))


def ortala(d, y, metin, f, renk, a=1.0, x0=0, x1=W):
    g = c.genislik(f, metin)
    d.text((x0 + (x1 - x0 - g) // 2, y), metin, font=f, fill=c.renk_a(renk, a))


def kart(d, x0, y0, x1, y1, a=1.0, vurgu=None, r=28):
    d.rounded_rectangle((x0, y0, x1, y1), radius=r, fill=c.renk_a(c.PANEL, 0.92 * a),
                        outline=c.renk_a(vurgu or c.PANEL_KENAR, a), width=3 if vurgu else 2)


def marka(d, ayar):
    f = c.font("kalin", 38)
    c.simsek(d, KENAR, 52, 44, c.VURGU)
    yazi(d, (KENAR + 54, 54), ayar["kanal"]["marka"], f, c.YAZI, 0.95)
    x = KENAR + 54 + c.genislik(f, ayar["kanal"]["marka"]) + 16
    yazi(d, (x, 58), "· gerçek ölçüm", c.font("orta", 32), c.SOLUK, 0.9)


class Foto:
    """Fotoğrafı bir kutuya kaplar, yavaş yakınlaştırır, köşeleri yuvarlatır."""

    def __init__(self, yol: Path, kutu: tuple[int, int, int, int]):
        self.kutu = kutu
        w, h = kutu[2] - kutu[0], kutu[3] - kutu[1]
        img = ImageOps.exif_transpose(Image.open(yol)).convert("RGB")
        self.kaynak = ImageOps.fit(img, (int(w * 1.15), int(h * 1.15)), Image.LANCZOS)
        self.w, self.h = w, h
        self.maske = Image.new("L", (w, h), 0)
        ImageDraw.Draw(self.maske).rounded_rectangle((0, 0, w - 1, h - 1), radius=28, fill=255)

    def yapistir(self, img: Image.Image, p: float, a: float):
        z = 1.15 - 0.12 * p
        kw, kh = int(self.w * z), int(self.h * z)
        sw, sh = self.kaynak.size
        x0, y0 = (sw - kw) // 2, (sh - kh) // 2
        k = self.kaynak.crop((x0, y0, x0 + kw, y0 + kh)).resize((self.w, self.h), Image.BILINEAR)
        m = self.maske if a >= 1 else self.maske.point(lambda v: int(v * a))
        img.paste(k, self.kutu[:2], m)


# ---- sahneler --------------------------------------------------------------
@dataclass
class Sahne:
    ad: str
    baslik: str                     # bölüm (chapter) adı; boşsa önceki bölüme dahil
    ciz: Callable                   # (img, d, t, sure)
    sure: float = 0.0
    ses: Path | None = None


def s_kanca(cihazlar, ayar):
    n = len(cihazlar)
    toplam = sum(tl(x) for x in cihazlar)
    pay = tl(cihazlar[-1]) / toplam * 100
    # gizemli çubuklar: gerçek oranlarla, ama isimsiz
    oranlar = [tl(x) / tl(cihazlar[-1]) for x in cihazlar]

    def ciz(img, d, t, S):
        p = c.yumusak(c.ilerleme(t, 0, 0.3))
        f_hap = c.font("kalin", 36)
        c.hap(d, KENAR + c.genislik(f_hap, "GERÇEK ÖLÇÜM") // 2 + 30, 250, "GERÇEK ÖLÇÜM", f_hap,
              c.VURGU, c.ZEMIN, 1.0)
        yazi(d, (KENAR, 340), f"{n} ev aletini prizden ölçtük", c.font("kalin", 64), c.YAZI)
        f = c.font("siyah", int(124 * (1.06 - 0.06 * p)))
        yazi(d, (KENAR, 440), f"Faturanın %{tam(pay)}'i", f, c.VURGU)
        yazi(d, (KENAR, 580), "TEK bir cihazdan", f, c.VURGU)
        g = int(760 * c.yumusak(c.ilerleme(t, 0.2, 0.8)))
        d.rounded_rectangle((KENAR, 740, KENAR + max(12, g), 752), radius=6, fill=c.renk_a(c.VURGU, 0.9))
        a, k = gir(t, 1.2)
        yazi(d, (KENAR, 790 + k), "Hangisi olduğunu sona sakladık.", c.font("yari", 46), c.SOLUK, a)
        # sağda isimsiz dikey çubuklar
        x0, taban, maxh = 1180, 900, 620
        cw = 96
        for i, o in enumerate(oranlar):
            pi = c.yumusak(c.ilerleme(t, 0.3 + 0.25 * i, 1.0))
            h = max(10, int(maxh * o * pi))
            x = x0 + i * (cw + 34)
            son = i == n - 1
            d.rounded_rectangle((x, taban - h, x + cw, taban), radius=14,
                                fill=c.renk_a(c.VURGU if son else c.CUBUK, 1.0))
            ortala(d, taban + 20, "?", c.font("siyah", 56), c.YAZI if son else c.SOLUK, pi, x, x + cw)
    return ciz


def s_yontem(cihazlar, ayar, uz):
    t_ = ayar["tarife"]
    kartlar = [
        ("Ölçüm", uz.get("olcum_cihazi", "enerji ölçer").capitalize()),
        ("Sürekli çalışanlar", "~30 gün prizde ölçüldü"),
        ("Kullanım başına", "Tek kullanım × haftalık sıklık"),
        ("Fiyat", f"{tr_sayi(t_['dusuk_kademe_tl'])} TL/kWh  ·  {t_['kademe_siniri_kwh']} kWh üstü "
                  f"{tr_sayi(t_['yuksek_kademe_tl'])} TL"),
    ]

    def ciz(img, d, t, S):
        a, k = gir(t, 0.05)
        yazi(d, (KENAR, 190 + k), "Nasıl ölçtük?", c.font("siyah", 92), c.YAZI, a)
        for i, (et, deg) in enumerate(kartlar):
            a, k = gir(t, 0.6 + 0.6 * i)
            y = 360 + i * 150 + k
            kart(d, KENAR, y, W - KENAR, y + 124, a)
            yazi(d, (KENAR + 44, y + 40), et, c.font("yari", 40), c.SOLUK, a)
            f = c.font("kalin", 50)
            while c.genislik(f, deg) > 1180 and f.size > 32:
                f = c.font("kalin", f.size - 2)
            yazi(d, (W - KENAR - 44 - c.genislik(f, deg), y + 36), deg, f, c.YAZI, a)
    return ciz


def kumulatif_serit(d, cihazlar, i, t, a=1.0):
    """Alt bant: şimdiye kadarki cihazların aylık TL'si üst üste."""
    toplam = sum(tl(x) for x in cihazlar)
    x0, x1, y0, h = KENAR, W - KENAR, 968, 34
    kum = sum(tl(x) for x in cihazlar[: i + 1])
    p = c.yumusak(c.ilerleme(t, 1.6, 1.2))
    goster = sum(tl(x) for x in cihazlar[:i]) + tl(cihazlar[i]) * p
    yazi(d, (x0, y0 - 52), f"Toplam fatura (ölçülen {i + 1}/{len(cihazlar)} cihaz)", c.font("yari", 32), c.SOLUK, a)
    deger = f"ayda {tam(goster)} TL"
    fv = c.font("kalin", 36)
    yazi(d, (x1 - c.genislik(fv, f"ayda {tam(kum)} TL"), y0 - 54), deger, fv, c.YAZI, a)
    d.rounded_rectangle((x0, y0, x1, y0 + h), radius=h // 2, fill=c.renk_a((255, 255, 255), 0.06 * a))
    bas = x0
    for j, x in enumerate(cihazlar[: i + 1]):
        g = (x1 - x0) * tl(x) / toplam * (p if j == i else 1)
        if g < 1:
            continue
        renk = c.VURGU if j == i else SEGMENT_RENK[j % len(SEGMENT_RENK)]
        d.rectangle((bas, y0, bas + g, y0 + h), fill=c.renk_a(renk, a))
        bas += g
    # uçları yuvarlat: zemin rengiyle köşe maskesi yerine kenarı yeniden çiz
    d.rounded_rectangle((x0, y0, x1, y0 + h), radius=h // 2, outline=c.renk_a(c.PANEL_KENAR, a), width=2)


def s_cihaz(cihazlar, i, ayar):
    x = cihazlar[i]
    h = x.ham
    n = len(cihazlar)
    sira = n - i
    foto_kutu = (KENAR, 150, 900, 860)
    g = x.gorseller()
    foto = Foto(g[0], foto_kutu) if g else None
    dus, yuk = x.tl(x.aylik_kwh)
    if x.tip == "donem":
        olcum = f"{h['gun']} gün prizden ölçüm: {tr_sayi(h['kwh'], 2)} kWh"
    else:
        ka = h.get("kullanim_adi", "kullanım")
        olcum = (f"Tek {ka}: {tr_sayi(h['kwh'], 3)} kWh · haftada {h['haftalik_kullanim']} {ka}")
    son = i == n - 1
    sag = 990

    def ciz(img, d, t, S):
        a0 = c.yumusak(c.ilerleme(t, 0, 0.5))
        if foto:
            foto.yapistir(img, t / S, a0)
        else:
            kart(d, *foto_kutu, a0)
            cx = (foto_kutu[0] + foto_kutu[2]) // 2
            c.simsek(d, cx - 70, 330, 140, c.VURGU, a0 * 0.9)
            f, sat = c.sigdir(x.kisa, "siyah", 84, 700, 2, 48)
            c.yazi_blok(d, sat, f, 530, c.YAZI, a0, W=foto_kutu[2] + foto_kutu[0])
        a, k = gir(t, 0.1)
        etiket = "EN ÇOK YAKAN" if son else f"{sira}. SIRA"
        f_h = c.font("kalin", 36)
        gh = c.genislik(f_h, etiket)
        d.rounded_rectangle((sag, 170 + k, sag + gh + 56, 230 + k), radius=30,
                            fill=c.renk_a(c.VURGU if son else c.PANEL_KENAR, a))
        yazi(d, (sag + 28, 178 + k), etiket, f_h, c.ZEMIN if son else c.YAZI, a)
        f_ad, s_ad = c.sigdir(x.ad, "kalin", 60, W - KENAR - sag, 2, 40)
        y = c.yazi_blok(d, s_ad, f_ad, 262 + k, c.YAZI, a, hiza="sol", x=sag, W=W)
        a2, k2 = gir(t, 0.5)
        f_o = c.font("orta", 34)
        while c.genislik(f_o, olcum) > W - KENAR - sag and f_o.size > 24:
            f_o = c.font("orta", f_o.size - 2)
        yazi(d, (sag, y + 10 + k2), olcum, f_o, c.SOLUK, a2)
        # büyük aylık TL sayacı
        v = dus * c.yumusak(c.ilerleme(t, 0.7, 1.4))
        a3 = c.yumusak(c.ilerleme(t, 0.6, 0.3))
        yazi(d, (sag, y + 90), "Aylık maliyet", c.font("yari", 40), c.SOLUK, a3)
        f_s = c.font("siyah", 190)
        metin = f"{tam(v)} TL"
        yazi(d, (sag - 6, y + 130), metin, f_s, c.VURGU, a3)
        a4, k4 = gir(t, 1.6)
        yb = y + 130 + 220
        yazi(d, (sag, yb + k4), f"{tr_sayi(x.aylik_kwh, 1)} kWh / ay", c.font("kalin", 46), c.YAZI, a4)
        yazi(d, (sag, yb + 66 + k4), f"Yüksek kademede {tam(yuk)} TL", c.font("orta", 38), c.YUKSEK, a4)
        if x.aylik_tahmini:
            yazi(d, (sag, yb + 120 + k4), "* kullanım sıklığına göre tahmini", c.font("orta", 30), c.SOLUK, a4)
        kumulatif_serit(d, cihazlar, i, t, a0)
    return ciz


def s_siralama(cihazlar, ayar):
    sirali = list(reversed(cihazlar))
    toplam = sum(tl(x) for x in cihazlar)
    en_b = tl(sirali[0])

    def ciz(img, d, t, S):
        a, k = gir(t, 0.05)
        yazi(d, (KENAR, 150 + k), "Aylık elektrik maliyeti: sıralama", c.font("siyah", 72), c.YAZI, a)
        yazi(d, (KENAR, 240 + k), "TL · düşük kademe tarife · Testigo gerçek ölçümleri", c.font("orta", 34), c.SOLUK, a)
        n = len(sirali)
        ust, alt = 330, 900
        adim = min(130, (alt - ust) / n)
        ch = int(min(52, adim * 0.42))
        etiket_g = 460
        bar_x0, bar_x1 = KENAR + etiket_g, W - KENAR - 330
        for j, x in enumerate(sirali):
            bas = 0.3 + 0.35 * j
            aj, kj = gir(t, bas)
            p = c.yumusak(c.ilerleme(t, bas + 0.1, 0.9))
            y = ust + j * adim
            vurgu = j == 0
            f_e = c.font("kalin" if vurgu else "yari", 44)
            et = x.kisa + ("*" if x.aylik_tahmini else "")
            yazi(d, (KENAR, y + kj), et, f_e, c.YAZI if vurgu else c.SOLUK, aj)
            cy = y + 4
            d.rounded_rectangle((bar_x0, cy, bar_x1, cy + ch), radius=ch // 2,
                                fill=c.renk_a((255, 255, 255), 0.05 * aj))
            g = max(ch, int((bar_x1 - bar_x0) * tl(x) / en_b * p))
            d.rounded_rectangle((bar_x0, cy, bar_x0 + g, cy + ch), radius=min(12, ch // 2),
                                fill=c.renk_a(c.VURGU if vurgu else c.CUBUK, aj))
            deger = f"{tam(tl(x))} TL"
            f_v = c.font("kalin", 46)
            yazi(d, (W - KENAR - 150 - c.genislik(f_v, deger), y - 2), deger, f_v,
                 c.YAZI if vurgu else c.SOLUK, aj * c.kis(p * 1.5))
            pay = f"%{tam(tl(x) / toplam * 100)}"
            f_p = c.font("orta", 36)
            yazi(d, (W - KENAR - c.genislik(f_p, pay), y + 4), pay, f_p, c.SOLUK, aj * c.kis(p * 1.5))
        an, _ = gir(t, 0.3 + 0.35 * n + 0.4)
        yazi(d, (KENAR, 950), f"Toplam: ayda {tam(toplam)} TL   ·   * kullanım sıklığına göre tahmini",
             c.font("orta", 32), c.SOLUK, an)
    return ciz


def s_kapanis(cihazlar, ayar):
    k = ayar["kanal"]

    def ciz(img, d, t, S):
        a1, k1 = gir(t, 0.05)
        a2, k2 = gir(t, 0.8)
        a3, k3 = gir(t, 1.6)
        ortala(d, 250 + k1, "Sen hangisini en çok kullanıyorsun?", c.font("siyah", 84), c.YAZI, a1)
        ortala(d, 370 + k1, "Yorumlara yaz, aylık maliyetini birlikte hesaplayalım.", c.font("yari", 46), c.SOLUK, a1)
        f_m = c.font("siyah", 120)
        g = c.genislik(f_m, k["marka"])
        x = (W - g - 110) // 2
        c.simsek(d, x, 560 + k2, 104, c.VURGU, a2)
        yazi(d, (x + 110, 548 + k2), k["marka"], f_m, c.YAZI, a2)
        ortala(d, 700 + k2, "Tüm ölçümler ve elektrik hesaplama aracı", c.font("yari", 44), c.YAZI, a2)
        c.hap(d, W // 2, int(780 + k3), k["site"], c.font("kalin", 58), c.VURGU, c.ZEMIN, a3, 44, 20)
    return ciz


# ---- süre / ses ------------------------------------------------------------
def ses_bul(ad: str) -> Path | None:
    for uz in (".mp3", ".wav", ".m4a", ".ogg", ".flac"):
        p = SES_DIR / f"{ad}{uz}"
        if p.exists():
            return p
    return None


def ses_suresi(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                        "default=nw=1:nk=1", str(p)], capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def sahneleri_kur(cihazlar, ayar, uz) -> tuple[list[Sahne], dict]:
    m = metinler(cihazlar, ayar, uz)
    n = len(cihazlar)
    sahneler = [Sahne("01_kanca", "Giriş", s_kanca(cihazlar, ayar)),
                Sahne("02_yontem", "Nasıl ölçtük?", s_yontem(cihazlar, ayar, uz))]
    for i, x in enumerate(cihazlar):
        # en çok yakanın adı bölüm başlığında görünmesin: sürpriz zaman çizelgesinde bozulmasın
        bolum = "1. sıra: en çok yakan cihaz" if i == n - 1 else f"{n - i}. {x.kisa} ayda kaç TL?"
        sahneler.append(Sahne(f"{i + 3:02d}_{x.id}", bolum, s_cihaz(cihazlar, i, ayar)))
    sahneler.append(Sahne(f"{n + 3:02d}_siralama", "Sonuç: aylık maliyet sıralaması", s_siralama(cihazlar, ayar)))
    sahneler.append(Sahne(f"{n + 4:02d}_kapanis", "", s_kapanis(cihazlar, ayar)))
    asgari = {"01_kanca": 6.0}
    for s in sahneler:
        s.ses = ses_bul(s.ad)
        if s.ses:
            s.sure = ses_suresi(s.ses) + SES_PAY + 0.4
        else:
            s.sure = len(m[s.ad].split()) / KELIME_SN + 1.5
        s.sure = max(s.sure, asgari.get(s.ad, 8.0))
    return sahneler, m


# ---- üretim ----------------------------------------------------------------
def kare_ciz(s: Sahne, t: float, duz: Image.Image, ayar) -> Image.Image:
    img = duz.copy()
    d = ImageDraw.Draw(img, "RGBA")
    marka(d, ayar)
    s.ciz(img, d, t, s.sure)
    return img


def kareleri_kaydet(sahneler, ayar):
    duz = c.duz_zemin(W, H)
    hedef = CIKTI / "kareler"
    hedef.mkdir(parents=True, exist_ok=True)
    for s in sahneler:
        kare_ciz(s, s.sure * 0.9, duz, ayar).save(hedef / f"{s.ad}.jpg", quality=90)
    print(f"Kareler: {hedef}")


def video_uret(sahneler, ayar, fps, cikis: Path):
    duz = c.duz_zemin(W, H)
    toplam = sum(s.sure for s in sahneler)
    kare_say = int(round(toplam * fps))
    cikis.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        sessiz = Path(tmp) / "goruntu.mp4"
        proc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(sessiz)],
            stdin=subprocess.PIPE)
        sinir, bas = [], 0.0
        for s in sahneler:
            sinir.append(bas)
            bas += s.sure
        j = 0
        try:
            for i in range(kare_say):
                t = i / fps
                while j < len(sahneler) - 1 and t >= sinir[j] + sahneler[j].sure:
                    j += 1
                    print(f"  {j + 1}/{len(sahneler)} {sahneler[j].ad}", flush=True)
                s = sahneler[j]
                tl_ = t - sinir[j]
                kare = kare_ciz(s, tl_, duz, ayar)
                kalan = s.sure - tl_
                if kalan < GECIS:
                    kare = Image.blend(duz, kare, max(0.0, kalan / GECIS))
                elif tl_ < GECIS and j > 0:
                    kare = Image.blend(duz, kare, tl_ / GECIS)
                proc.stdin.write(kare.tobytes())
        finally:
            proc.stdin.close()
            proc.wait()
        if proc.returncode != 0:
            raise RuntimeError("ffmpeg görüntü kodlaması başarısız")

        # ses: seslendirme parçaları kendi sahne başlangıcına yerleşir + müzik altlığı
        sesler = [(sinir[k] + 0.4, s.ses) for k, s in enumerate(sahneler) if s.ses]
        muzik = muzik_sec("uzun") or ambiyans_uret(toplam + 0.5, Path(tmp) / "muzik.wav", "uzun")
        db = -22 if sesler else ayar["video"]["muzik_ses_db"]
        girdiler = ["-i", str(sessiz), "-stream_loop", "-1", "-i", str(muzik)]
        filtre = [f"[1:a]volume={db}dB,afade=t=out:st={max(0, toplam - 2):.2f}:d=2,atrim=0:{toplam:.2f}[m]"]
        etiketler = ["[m]"]
        for k, (bas_sn, yol) in enumerate(sesler):
            girdiler += ["-i", str(yol)]
            ms = int(bas_sn * 1000)
            filtre.append(f"[{k + 2}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{k}]")
            etiketler.append(f"[v{k}]")
        filtre.append(f"{''.join(etiketler)}amix=inputs={len(etiketler)}:duration=first:normalize=0[a]")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *girdiler, "-filter_complex", ";".join(filtre),
                        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-t", f"{toplam:.2f}", "-movflags", "+faststart", str(cikis)], check=True)
    return sinir


def zaman(sn: float) -> str:
    sn = int(sn)
    return f"{sn // 60:02d}:{sn % 60:02d}"


def aciklama_yaz(sahneler, sinir, cihazlar, ayar, uz) -> dict:
    n = len(cihazlar)
    baslik = uz.get("baslik", "{n} Ev Aletini Ölçtüm").format(n=n)
    t = ayar["tarife"]
    satir = [f"{n} ev aletini prizden ölçtük ve aylık elektrik maliyetini en azdan en çoğa sıraladık.", "",
             "Bölümler:"]
    for s, b in zip(sahneler, sinir):
        if s.baslik:
            satir.append(f"{zaman(b)} {s.baslik}")
    satir += ["", "Aylık maliyetler (düşük kademe):"]
    for x in reversed(cihazlar):
        satir.append(f"• {x.ad}: {tam(tl(x))} TL / ay" + (" (tahmini kullanım)" if x.aylik_tahmini else ""))
    satir += ["", f"Hesaplama: aylık ilk {t['kademe_siniri_kwh']} kWh {tr_sayi(t['dusuk_kademe_tl'])} TL/kWh, "
                  f"üzeri {tr_sayi(t['yuksek_kademe_tl'])} TL/kWh.",
              "", "Tüm ölçümler ve elektrik hesaplama aracı:", ayar["kanal"]["site_url"],
              "", "#elektriktüketimi #elektrikfaturası #testigo"]
    etiketler = ["elektrik tüketimi", "ev aletleri elektrik tüketimi", "elektrik faturası",
                 "hangi cihaz çok elektrik yakar", "testigo", "gerçek ölçüm"]
    for x in cihazlar:
        etiketler += x.ham.get("etiketler", [])[:2]
    temiz, top = [], 0
    for e in dict.fromkeys(etiketler):
        if top + len(e) + 2 > 480:
            break
        temiz.append(e)
        top += len(e) + 2
    return {"baslik": baslik[:100], "aciklama": "\n".join(satir), "etiketler": temiz}


def kapak(cihazlar, ayar, cikis: Path):
    Wk, Hk = 1280, 720
    img = c.duz_zemin(Wk, Hk)
    d = ImageDraw.Draw(img, "RGBA")
    n = len(cihazlar)
    toplam = sum(tl(x) for x in cihazlar)
    pay = tl(cihazlar[-1]) / toplam * 100
    c.simsek(d, 60, 48, 40, c.VURGU)
    yazi(d, (108, 50), ayar["kanal"]["marka"], c.font("kalin", 36), c.YAZI)
    yazi(d, (60, 130), f"{n} CİHAZI ÖLÇTÜM", c.font("siyah", 84), c.YAZI)
    yazi(d, (60, 250), "FATURANIN", c.font("siyah", 64), c.YAZI)
    yazi(d, (60, 320), f"%{tam(pay)}'i", c.font("siyah", 160), c.VURGU)
    yazi(d, (60, 510), "TEK CİHAZDAN!", c.font("siyah", 88), c.VURGU)
    x0, taban = 820, 640
    oran = [tl(x) / tl(cihazlar[-1]) for x in cihazlar]
    for i, o in enumerate(oran):
        h = max(14, int(480 * o))
        x = x0 + i * 82
        d.rounded_rectangle((x, taban - h, x + 62, taban), radius=10,
                            fill=c.VURGU if i == n - 1 else c.CUBUK)
    img.save(cikis, quality=92)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metin", action="store_true", help="sadece seslendirme metnini yaz")
    ap.add_argument("--kareler", action="store_true", help="sadece her sahneden bir JPG")
    a = ap.parse_args()
    ayar, uz = ayarlar()
    cihazlar = cihazlar_hazirla(ayar, uz)
    if len(cihazlar) < 3:
        raise SystemExit("En az 3 cihaz gerekli")
    sahneler, m = sahneleri_kur(cihazlar, ayar, uz)
    CIKTI.mkdir(parents=True, exist_ok=True)

    metin_yol = CIKTI / "seslendirme_metni.txt"
    with metin_yol.open("w", encoding="utf-8") as f:
        f.write("Her bölümü ayrı ses dosyası yap, seslendirme/ klasörüne dosya adıyla koy "
                "(örn. seslendirme/01_kanca.mp3).\n\n")
        for s in sahneler:
            f.write(f"=== {s.ad} ===\n{m[s.ad]}\n\n")
    print(f"Seslendirme metni: {metin_yol}")
    print("Sıra (azdan çoğa): " + " → ".join(f"{x.kisa} {tam(tl(x))} TL" for x in cihazlar))
    for s in sahneler:
        print(f"  {s.ad:40} {s.sure:5.1f} sn  {'ses ✓' if s.ses else 'ses yok (tahmini süre)'}")
    print(f"Toplam süre: {zaman(sum(s.sure for s in sahneler))}")
    if a.metin:
        return
    if a.kareler:
        kareleri_kaydet(sahneler, ayar)
        return
    mp4 = CIKTI / "uzun_video.mp4"
    sinir = video_uret(sahneler, ayar, uz.get("fps", 30), mp4)
    kapak(cihazlar, ayar, CIKTI / "kapak.jpg")
    meta = aciklama_yaz(sahneler, sinir, cihazlar, ayar, uz)
    (CIKTI / "youtube.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    (CIKTI / "aciklama.txt").write_text(meta["baslik"] + "\n\n" + meta["aciklama"], encoding="utf-8")
    print(f"Video: {mp4} ({mp4.stat().st_size / 1e6:.1f} MB)\nKapak: {CIKTI / 'kapak.jpg'}\n"
          f"Açıklama + bölümler: {CIKTI / 'aciklama.txt'}")


if __name__ == "__main__":
    main()
