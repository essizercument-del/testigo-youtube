"""Video sahneleri ve plan türüne göre sahne listesi."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from PIL import Image, ImageDraw

from . import cizim as c
from .veri import Cihaz, Plan, sure_metni, tr_sayi, tr_tl

W, H = 1080, 1920
ICERIK_G = W - 2 * c.KENAR


@dataclass
class Sahne:
    sure: float
    ciz: Callable[[Image.Image, ImageDraw.ImageDraw, float], None]
    zemin: object | None = None          # FotoZemin / KlipZemin / None
    ad: str = ""


def _gir(t, bas, sure=0.45):
    """(alfa, kayma_px) — aşağıdan yukarı süzülerek gelme."""
    p = c.yumusak(c.ilerleme(t, bas, sure))
    return p, (1 - p) * 48


# ---- ortak parçalar --------------------------------------------------------
def marka_basligi(d: ImageDraw.ImageDraw, marka: str):
    f = c.font("kalin", 40)
    c.simsek(d, c.KENAR, 166, 46, c.VURGU)
    d.text((c.KENAR + 56, 168), marka, font=f, fill=c.renk_a(c.YAZI, 0.95))
    x = c.KENAR + 56 + c.genislik(f, marka) + 18
    d.text((x, 172), "· gerçek ölçüm", font=c.font("orta", 34), fill=c.renk_a(c.SOLUK, 0.9))


def kart(d, x0, y0, x1, y1, a=1.0, vurgu=None):
    d.rounded_rectangle((x0, y0, x1, y1), radius=28, fill=c.renk_a(c.PANEL, 0.92 * a),
                        outline=c.renk_a(vurgu or c.PANEL_KENAR, a), width=3 if vurgu else 2)


def sayac(t, bas, sure, hedef):
    return hedef * c.yumusak(c.ilerleme(t, bas, sure))


# ---- sahne fabrikaları -----------------------------------------------------
def kanca(ust: str, buyuk: str, alt: str | None = None, zemin=None, sure=3.2) -> Sahne:
    def ciz(img, d, t):
        a1, k1 = _gir(t, 0.05)
        a2, k2 = _gir(t, 0.25, 0.55)
        a3, k3 = _gir(t, 0.9)
        f_ust, s_ust = c.sigdir(ust, "yari", 54, ICERIK_G, 2, 40)
        f_b, s_b = c.sigdir(buyuk, "siyah", 128, ICERIK_G, 4, 72)
        blok = len(s_b) * int(f_b.size * 1.08)
        y = 900 - blok // 2
        c.hap(d, W // 2, y - 150, "GERÇEK ÖLÇÜM", c.font("kalin", 34), c.VURGU, c.ZEMIN, a1)
        y = c.yazi_blok(d, s_ust, f_ust, y - 40, c.SOLUK, a1, kayma=k1) + 20
        y = c.yazi_blok(d, s_b, f_b, y, c.YAZI, a2, aralik=1.08, kayma=k2)
        if alt:
            f_a, s_a = c.sigdir(alt, "yari", 52, ICERIK_G, 2, 40)
            c.yazi_blok(d, s_a, f_a, y + 40, c.VURGU, a3, kayma=k3)
    return Sahne(sure, ciz, zemin, "kanca")


def olcum(baslik: str, deger: float, birim: str, basamak: int, kartlar: list[tuple[str, str]],
          not_: str | None = None, zemin=None, sure=6.0) -> Sahne:
    def ciz(img, d, t):
        a1, k1 = _gir(t, 0.05)
        f_b, s_b = c.sigdir(baslik, "kalin", 64, ICERIK_G, 3, 44)
        y = c.yazi_blok(d, s_b, f_b, 560, c.YAZI, a1, kayma=k1)
        # büyük sayaç
        v = sayac(t, 0.35, 2.2, deger)
        metin = tr_sayi(v, basamak)
        f_s = c.font("siyah", 220)
        while c.genislik(f_s, metin) > ICERIK_G and f_s.size > 120:
            f_s = c.font("siyah", f_s.size - 10)
        a2 = c.yumusak(c.ilerleme(t, 0.3, 0.35))
        hedef_metin = tr_sayi(deger, basamak)          # genişliği sabit tut: titreme olmasın
        sx = (W - c.genislik(f_s, hedef_metin)) // 2
        d.text((sx, y + 70), metin, font=f_s, fill=c.renk_a(c.VURGU, a2))
        alt = y + 70 + f_s.getbbox(hedef_metin)[3]
        f_bi = c.font("kalin", 72)
        d.text(((W - c.genislik(f_bi, birim)) // 2, alt + 28), birim,
               font=f_bi, fill=c.renk_a(c.YAZI, a2))
        y = alt + 28 + 72 + 90
        # bilgi kartları
        for i, (etiket, deg) in enumerate(kartlar):
            a, k = _gir(t, 1.6 + 0.35 * i)
            y0 = y + i * 170 + k
            kart(d, c.KENAR, y0, W - c.KENAR, y0 + 140, a)
            d.text((c.KENAR + 40, y0 + 46), etiket, font=c.font("yari", 44), fill=c.renk_a(c.SOLUK, a))
            fd = c.font("kalin", 56)
            d.text((W - c.KENAR - 40 - c.genislik(fd, deg), y0 + 40), deg, font=fd, fill=c.renk_a(c.YAZI, a))
        if not_:
            a, _ = _gir(t, 2.4)
            f_n, s_n = c.sigdir(not_, "orta", 38, ICERIK_G, 2, 30)
            c.yazi_blok(d, s_n, f_n, y + len(kartlar) * 170 + 20, c.SOLUK, a)
    return Sahne(sure, ciz, zemin, "olcum")


def cubuk_grafik(baslik: str, alt_baslik: str, satirlar: list[tuple[str, float, str, bool]],
                 dipnot: str | None = None, sure=8.0, kademeli=0.25) -> Sahne:
    """satirlar: (etiket, değer, değer_metni, vurgulu). Yatay çubuklar sırayla büyür."""
    en_buyuk = max(v for _, v, _, _ in satirlar) or 1

    def ciz(img, d, t):
        a1, k1 = _gir(t, 0.05)
        f_b, s_b = c.sigdir(baslik, "kalin", 68, ICERIK_G, 2, 48)
        y = c.yazi_blok(d, s_b, f_b, 400, c.YAZI, a1, hiza="sol", kayma=k1)
        c.yazi_blok(d, [alt_baslik], c.font("orta", 38), y + 6, c.SOLUK, a1, hiza="sol", kayma=k1)
        n = len(satirlar)
        alan_ust, alan_alt = y + 110, c.GUVENLI_ALT - (90 if dipnot else 20)
        adim = min(230, (alan_alt - alan_ust) / n)
        cubuk_h = int(min(68, adim * 0.36))
        f_e = c.font("yari", int(min(44, adim * 0.26)))
        f_v = c.font("kalin", int(min(48, adim * 0.28)))
        max_cubuk = ICERIK_G
        for i, (etiket, v, vm, vurgu) in enumerate(satirlar):
            bas = 0.5 + i * kademeli
            a, k = _gir(t, bas, 0.4)
            p = c.yumusak(c.ilerleme(t, bas + 0.1, 1.1))
            y0 = alan_ust + i * adim
            renk_e = c.YAZI if vurgu else c.SOLUK
            d.text((c.KENAR, y0 + k), etiket, font=f_e, fill=c.renk_a(renk_e, a))
            # değer etiketi sağa hizalı, satır başlığıyla aynı hizada
            d.text((W - c.KENAR - c.genislik(f_v, vm), y0 + k - 2), vm, font=f_v,
                   fill=c.renk_a(c.YAZI if vurgu else c.SOLUK, a * c.kis(p * 1.5)))
            cy = y0 + int(f_e.size * 1.35)
            # iz (arka hat)
            d.rounded_rectangle((c.KENAR, cy, c.KENAR + max_cubuk, cy + cubuk_h), radius=cubuk_h // 2,
                                fill=c.renk_a((255, 255, 255), 0.05 * a))
            g = max(cubuk_h, int(max_cubuk * (v / en_buyuk) * p))
            d.rounded_rectangle((c.KENAR, cy, c.KENAR + g, cy + cubuk_h), radius=min(12, cubuk_h // 2),
                                fill=c.renk_a(c.VURGU if vurgu else c.CUBUK, a))
        if dipnot:
            a, _ = _gir(t, 0.5 + n * kademeli + 0.6)
            f_n, s_n = c.sigdir(dipnot, "orta", 36, ICERIK_G, 2, 28)
            c.yazi_blok(d, s_n, f_n, c.GUVENLI_ALT - 70, c.SOLUK, a, hiza="sol")
    return Sahne(sure, ciz, None, "grafik")


def sonuc(baslik: str, kartlar: list[tuple[str, str, str | None, tuple]], not_: str | None = None,
          sure=6.5) -> Sahne:
    """kartlar: (etiket, büyük değer, alt satır, değer rengi)."""
    def ciz(img, d, t):
        a1, k1 = _gir(t, 0.05)
        f_b, s_b = c.sigdir(baslik, "kalin", 76, ICERIK_G, 3, 50)
        y = c.yazi_blok(d, s_b, f_b, 520, c.YAZI, a1, kayma=k1) + 60
        for i, (etiket, deger, alt, renk) in enumerate(kartlar):
            a, k = _gir(t, 0.5 + 0.5 * i, 0.5)
            f_e, s_e = c.sigdir(etiket, "yari", 46, ICERIK_G - 80, 1, 32)
            f_d = c.font("siyah", 120)
            while c.genislik(f_d, deger) > ICERIK_G - 88 and f_d.size > 60:
                f_d = c.font("siyah", f_d.size - 6)
            f_alt = c.font("orta", 38)
            deger_alt = 96 + f_d.getbbox(deger)[3]           # kart üstüne göre değerin alt kenarı
            yuk = deger_alt + (30 + 46 + 34 if alt else 44)
            y0 = y + k
            kart(d, c.KENAR, y0, W - c.KENAR, y0 + yuk, a, vurgu=renk)
            d.text((c.KENAR + 44, y0 + 36), s_e[0], font=f_e, fill=c.renk_a(c.SOLUK, a))
            d.text((c.KENAR + 40, y0 + 96), deger, font=f_d, fill=c.renk_a(renk, a))
            if alt:
                d.text((c.KENAR + 44, y0 + deger_alt + 30), alt, font=f_alt, fill=c.renk_a(c.SOLUK, a))
            y += yuk + 40
        if not_:
            a, _ = _gir(t, 0.6 + 0.5 * len(kartlar))
            f_n, s_n = c.sigdir(not_, "orta", 36, ICERIK_G, 2, 28)
            c.yazi_blok(d, s_n, f_n, y + 10, c.SOLUK, a)
    return Sahne(sure, ciz, None, "sonuc")


def kapanis(ayar: dict, ek: str = "Tüm ölçümler ve hesaplama aracı", sure=3.4) -> Sahne:
    k = ayar["kanal"]

    def ciz(img, d, t):
        a1, k1 = _gir(t, 0.05)
        a2, k2 = _gir(t, 0.4)
        a3, k3 = _gir(t, 0.8)
        f_m = c.font("siyah", 150)
        g = c.genislik(f_m, k["marka"])
        x = (W - g - 130) // 2
        c.simsek(d, x, 720 + k1, 124, c.VURGU, a1)
        d.text((x + 130, 710 + k1), k["marka"], font=f_m, fill=c.renk_a(c.YAZI, a1))
        c.yazi_blok(d, [k["slogan"]], c.font("yari", 48), 910, c.SOLUK, a1, kayma=k1)
        c.yazi_blok(d, [ek], c.font("yari", 50), 1090, c.YAZI, a2, kayma=k2)
        c.hap(d, W // 2, int(1180 + k2), k["site"], c.font("kalin", 64), c.VURGU, c.ZEMIN, a2, 44, 22)
        c.yazi_blok(d, ["Takip et: her gün yeni bir ölçüm"], c.font("orta", 42), 1370, c.SOLUK, a3,
                    kayma=k3)
    return Sahne(sure, ciz, None, "kapanis")


# ---- plan -> sahneler ------------------------------------------------------
def _tarife_notu(ayar):
    t = ayar["tarife"]
    return (f"Birim fiyat: {tr_sayi(t['dusuk_kademe_tl'])} TL/kWh\n"
            f"Aylık {t['kademe_siniri_kwh']} kWh üstü: {tr_sayi(t['yuksek_kademe_tl'])} TL/kWh")


def kwh_metni(x: Cihaz) -> str:
    return f"{tr_sayi(x.aylik_kwh, 1)} kWh"


def tl_metni(x: Cihaz) -> str:
    return tr_tl(x.tl(x.aylik_kwh)[0])


def grafik_satirlari(cihazlar: list[Cihaz], vurgulu: set[str], metin=kwh_metni, en_fazla: int = 7):
    sirali = sorted(cihazlar, key=lambda x: x.aylik_kwh, reverse=True)
    if len(sirali) > en_fazla:  # vurgulananlar her zaman kalsın
        kalan = [x for x in sirali if x.id in vurgulu]
        for x in sirali:
            if len(kalan) >= en_fazla:
                break
            if x not in kalan:
                kalan.append(x)
        sirali = sorted(kalan, key=lambda x: x.aylik_kwh, reverse=True)
    satirlar = []
    for x in sirali:
        yildiz = "*" if x.aylik_tahmini else ""
        satirlar.append((x.kisa + yildiz, x.aylik_kwh, metin(x), x.id in vurgulu))
    tahmin_var = any(x.aylik_tahmini for x in sirali)
    return satirlar, tahmin_var


def sahneleri_kur(plan: Plan, tum: list[Cihaz], ayar: dict, fps: int) -> list[Sahne]:
    maske = c.karartma_maskesi(W, H)
    aylikli = [x for x in tum if x.aylik_kwh]

    def foto(cihaz, i, yon=1):
        g = cihaz.gorseller()
        return c.FotoZemin(g[i % len(g)], W, H, maske, yon) if g else None

    def klip_ya_da_foto(cihaz):
        k = cihaz.klipler()
        if k:
            return c.KlipZemin(k[0], W, H, fps, maske)
        return foto(cihaz, 1, -1)

    if plan.tur == "tek":
        x = plan.cihazlar[0]
        h = x.ham
        sahneler = []
        if x.tip == "donem":
            soru = h.get("soru") or "Ayda kaç TL elektrik yakıyor?"
            sahneler.append(kanca(x.ad, soru, zemin=foto(x, 0)))
            kartlar = []
            if h.get("anlik_watt"):
                kartlar.append(("Anlık güç", f"{tr_sayi(h['anlik_watt'], 0)} W"))
            kartlar.append(("Günlük ortalama", f"{tr_sayi(h['kwh'] / h['gun'], 2)} kWh"))
            sahneler.append(olcum(f"{h['gun']} gün boyunca prizden ölçtük", h["kwh"], "kWh", 2,
                                  kartlar, h.get("not"), zemin=klip_ya_da_foto(x)))
        else:
            ka = h.get("kullanim_adi", "kullanım")
            soru = h.get("soru") or f"Bir {ka} kaç TL'ye mal oluyor?"
            sahneler.append(kanca(x.ad, soru, zemin=foto(x, 0)))
            kartlar = []
            if h.get("sure_sn"):
                kartlar.append((f"{ka.capitalize()} süresi", sure_metni(h["sure_sn"])))
            if h.get("anlik_watt"):
                kartlar.append(("Anlık güç", f"{tr_sayi(h['anlik_watt'], 0)} W"))
            sahneler.append(olcum(f"Tek {ka} ölçümü", h["kwh"], "kWh", 3, kartlar, h.get("not"),
                                  zemin=klip_ya_da_foto(x)))

        if x.aylik_kwh and len(aylikli) >= 2:
            satirlar, tahmin = grafik_satirlari(aylikli, {x.id})
            sahneler.append(cubuk_grafik("Aylık tüketim kıyası", "kWh · Testigo gerçek ölçümleri",
                                         satirlar, "* kullanım sıklığına göre tahmini" if tahmin else None))

        if x.tip == "donem":
            dus, yuk = x.tl(x.aylik_kwh)
            sinir = ayar["tarife"]["kademe_siniri_kwh"]
            baslik = "Aylık faturaya etkisi" if 28 <= h["gun"] <= 31 else "Aylık faturaya etkisi (30 gün)"
            sahneler.append(sonuc(baslik, [
                (f"Ev {sinir} kWh altındaysa", tr_tl(dus), None, c.DUSUK),
                (f"Ev {sinir} kWh üstündeyse", tr_tl(yuk), None, c.YUKSEK),
            ], _tarife_notu(ayar)))
        else:
            ka = h.get("kullanim_adi", "kullanım")
            d1, y1 = x.tl(h["kwh"])
            kartlar = [(f"Tek {ka}", tr_tl(d1), f"Yüksek kademede {tr_tl(y1)}", c.DUSUK)]
            if x.aylik_kwh:
                d2, y2 = x.tl(x.aylik_kwh)
                kartlar.append((f"Aylık (haftada {h['haftalik_kullanim']} {ka})", tr_tl(d2),
                                f"Yüksek kademede {tr_tl(y2)}", c.VURGU))
            sahneler.append(sonuc("Faturaya etkisi", kartlar, _tarife_notu(ayar)))
        sahneler.append(kapanis(ayar))
        return sahneler

    if plan.tur == "karsilastirma":
        a, b = plan.cihazlar
        cok, az = (a, b) if a.aylik_kwh >= b.aylik_kwh else (b, a)
        satirlar, tahmin = grafik_satirlari([a, b], {cok.id},
                                            lambda x: f"{kwh_metni(x)} · {tl_metni(x)}")
        oran = cok.aylik_kwh / az.aylik_kwh
        fark = cok.tl(cok.aylik_kwh)[0] - az.tl(az.aylik_kwh)[0]
        return [
            kanca("Hangisi ayda daha çok yakar?", f"{a.kisa} mı,\n{b.kisa} mı?", zemin=foto(a, 0)),
            cubuk_grafik("Aylık tüketim", "kWh · düşük kademe TL", satirlar,
                         "* kullanım sıklığına göre tahmini" if tahmin else None, sure=6.5, kademeli=0.5),
            sonuc(f"Daha çok yakan: {cok.kisa}", [
                ("Aylık fark", f"+{tr_tl(fark)}", "düşük kademe tarifeyle", c.VURGU),
                ("Tüketim oranı", f"{tr_sayi(oran, 1)} kat", f"{cok.kisa} / {az.kisa}", c.YAZI),
            ], _tarife_notu(ayar)),
            kapanis(ayar),
        ]

    if plan.tur == "siralama":
        satirlar, tahmin = grafik_satirlari(plan.cihazlar, set(), tl_metni)
        satirlar[0] = (*satirlar[0][:3], True)
        en = max(plan.cihazlar, key=lambda x: x.aylik_kwh)
        dus, yuk = en.tl(en.aylik_kwh)
        return [
            kanca(f"{len(plan.cihazlar)} cihaz, gerçek ölçüm", "Evdeki cihazlar ayda kaç TL yakıyor?"),
            cubuk_grafik("Aylık elektrik maliyeti", "TL · düşük kademe tarife", satirlar,
                         "* kullanım sıklığına göre tahmini" if tahmin else None, sure=9.0, kademeli=0.45),
            sonuc("En çok yakan", [(en.kisa, tr_tl(dus), f"Yüksek kademede {tr_tl(yuk)}", c.VURGU)],
                  _tarife_notu(ayar), sure=5.0),
            kapanis(ayar),
        ]

    raise ValueError(plan.tur)
