"""YouTube başlık, açıklama ve etiketleri."""
from __future__ import annotations

from .veri import Cihaz, Plan, sure_metni, tr_sayi, tr_tl


def _kisalt(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _tarife(ayar):
    t = ayar["tarife"]
    return (f"Hesaplama: aylık ilk {t['kademe_siniri_kwh']} kWh {tr_sayi(t['dusuk_kademe_tl'])} TL/kWh, "
            f"üzeri {tr_sayi(t['yuksek_kademe_tl'])} TL/kWh (kademeli konut tarifesi).")


def _alt_bilgi(ayar, linkler: list[str]):
    site = ayar["kanal"]["site_url"]
    satirlar = ["", "Tüm ölçümler ve elektrik hesaplama aracı:"]
    for l in dict.fromkeys(linkler + [site]):
        satirlar.append(l)
    satirlar += ["", "Testigo: ürünleri gerçek ölçümle test ediyoruz. Her gün yeni bir ölçüm.",
                 "", "#elektriktüketimi #elektrikfaturası #testigo #shorts"]
    return satirlar


def meta_olustur(plan: Plan, ayar: dict) -> dict:
    etiketler = ["elektrik tüketimi", "elektrik faturası", "ne kadar elektrik yakar", "testigo",
                 "kwh hesaplama", "gerçek ölçüm"]
    if plan.tur == "tek":
        x: Cihaz = plan.cihazlar[0]
        h = x.ham
        if x.tip == "donem":
            dus, yuk = x.tl(x.aylik_kwh)
            baslik = f"{x.ad} Ayda {tr_sayi(dus, 0)} TL Elektrik Yakıyor! {h['gun']} Gün Prizden Ölçtüm"
            govde = [f"{x.ad} cihazını {h['gun']} gün boyunca prizden ölçtük.",
                     "",
                     f"Ölçülen tüketim: {tr_sayi(h['kwh'], 2)} kWh ({h['gun']} gün)",
                     f"Aylık maliyet: {tr_tl(dus)} (düşük kademe) / {tr_tl(yuk)} (yüksek kademe)"]
        else:
            ka = h.get("kullanim_adi", "kullanım")
            d1, _ = x.tl(h["kwh"])
            baslik = f"{x.ad}: Bir {ka.capitalize()} Kaç TL? Gerçek Ölçüm"
            govde = [f"{x.ad} için tek {ka} tüketimini ölçtük.", "",
                     f"Tek {ka}: {tr_sayi(h['kwh'], 3)} kWh = {tr_tl(d1)}"]
            if h.get("sure_sn"):
                govde.append(f"Süre: {sure_metni(h['sure_sn'])}")
            if h.get("anlik_watt"):
                govde.append(f"Anlık güç: {tr_sayi(h['anlik_watt'], 0)} W")
            if x.aylik_kwh:
                d2, y2 = x.tl(x.aylik_kwh)
                govde.append(f"Haftada {h['haftalik_kullanim']} {ka} ile aylık: {tr_tl(d2)} – {tr_tl(y2)}")
        govde.append(_tarife(ayar))
        etiketler = h.get("etiketler", []) + etiketler
        linkler = [x.link] if x.link else []
    elif plan.tur == "karsilastirma":
        a, b = plan.cihazlar
        baslik = f"{a.kisa} mı {b.kisa} mı? Hangisi Daha Çok Elektrik Yakar?"
        govde = ["Gerçek ölçümlerle aylık elektrik tüketimi karşılaştırması.", ""]
        for x in (a, b):
            govde.append(f"{x.ad}: {tr_sayi(x.aylik_kwh, 1)} kWh/ay ≈ {tr_tl(x.tl(x.aylik_kwh)[0])}"
                         + (" (tahmini kullanım)" if x.aylik_tahmini else ""))
        govde.append(_tarife(ayar))
        etiketler = a.ham.get("etiketler", [])[:3] + b.ham.get("etiketler", [])[:3] + etiketler
        linkler = [x.link for x in (a, b) if x.link]
    else:
        baslik = f"{len(plan.cihazlar)} Ev Aleti Ayda Kaç TL Elektrik Yakıyor? Gerçek Ölçüm"
        govde = ["Ölçtüğümüz ev aletlerinin aylık elektrik maliyeti:", ""]
        for x in sorted(plan.cihazlar, key=lambda x: x.aylik_kwh, reverse=True):
            govde.append(f"• {x.ad}: {tr_tl(x.tl(x.aylik_kwh)[0])}" + (" (tahmini)" if x.aylik_tahmini else ""))
        govde.append(_tarife(ayar))
        linkler = []
    baslik = _kisalt(baslik, 100)
    aciklama = "\n".join(govde + _alt_bilgi(ayar, linkler))
    # YouTube etiket toplamı 500 karakteri geçmemeli
    temiz, toplam = [], 0
    for e in dict.fromkeys(etiketler):
        if toplam + len(e) + 2 > 480:
            break
        temiz.append(e)
        toplam += len(e) + 2
    return {"baslik": baslik, "aciklama": aciklama, "etiketler": temiz}
