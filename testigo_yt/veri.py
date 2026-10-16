"""Ölçüm verisini okur, TL hesaplarını yapar ve sıradaki videoyu seçer."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
VERI = KOK / "data" / "olcumler.json"
DURUM = KOK / "data" / "durum.json"
AYAR = KOK / "config.json"
MEDYA = KOK / "media"

HAFTA_AY = 52 / 12  # ayda ortalama hafta sayısı


def ayar_yukle() -> dict:
    return json.loads(AYAR.read_text(encoding="utf-8"))


def tr_sayi(x: float, basamak: int = 2) -> str:
    """1234.5 -> '1.234,50' (Türkçe biçim)."""
    s = f"{x:,.{basamak}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def tr_tl(x: float) -> str:
    return f"{tr_sayi(x, 2)} TL"


def sure_metni(sn: int) -> str:
    dk, s = divmod(int(sn), 60)
    if dk and s:
        return f"{dk} dk {s} sn"
    return f"{dk} dk" if dk else f"{s} sn"


@dataclass
class Cihaz:
    ham: dict
    tarife: dict

    @property
    def id(self) -> str:
        return self.ham["id"]

    @property
    def ad(self) -> str:
        return self.ham["cihaz"]

    @property
    def kisa(self) -> str:
        return self.ham.get("kisa_ad") or self.ad

    @property
    def tip(self) -> str:
        return self.ham["tip"]

    @property
    def link(self) -> str | None:
        return self.ham.get("link")

    # ---- aylık tüketim -------------------------------------------------
    @property
    def aylik_kwh(self) -> float | None:
        """Aylık kWh. Dönem ölçümünde 28-31 gün ölçülen değer olduğu gibi
        kullanılır (sitedeki tabloyla aynı), diğer sürelerde 30 güne ölçeklenir."""
        if self.tip == "donem":
            gun = self.ham["gun"]
            if 28 <= gun <= 31:
                return self.ham["kwh"]
            return self.ham["kwh"] / gun * 30
        hk = self.ham.get("haftalik_kullanim")
        if hk:
            return self.ham["kwh"] * hk * HAFTA_AY
        return None

    @property
    def aylik_tahmini(self) -> bool:
        return self.tip == "kullanim"

    def tl(self, kwh: float) -> tuple[float, float]:
        return kwh * self.tarife["dusuk_kademe_tl"], kwh * self.tarife["yuksek_kademe_tl"]

    @property
    def medya_klasoru(self) -> Path:
        return MEDYA / self.id

    def gorseller(self) -> list[Path]:
        d = self.medya_klasoru
        if not d.is_dir():
            return []
        return sorted(p for p in d.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})

    def klipler(self) -> list[Path]:
        d = self.medya_klasoru
        if not d.is_dir():
            return []
        return sorted(p for p in d.iterdir() if p.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"})


def cihazlari_yukle(ayar: dict | None = None) -> list[Cihaz]:
    ayar = ayar or ayar_yukle()
    ham = json.loads(VERI.read_text(encoding="utf-8"))
    idler = [h["id"] for h in ham]
    if len(idler) != len(set(idler)):
        raise ValueError("olcumler.json içinde tekrar eden id var")
    return [Cihaz(h, ayar["tarife"]) for h in ham]


# ---- video planı -----------------------------------------------------------
@dataclass
class Plan:
    anahtar: str            # durum.json'da tutulan benzersiz ad
    tur: str                # tek | karsilastirma | siralama
    cihazlar: list[Cihaz] = field(default_factory=list)


def tum_planlar(cihazlar: list[Cihaz]) -> list[Plan]:
    """Öncelik: önce her cihazın kendi videosu, sonra sıralama, sonra ikili kıyaslar.
    Yeni ölçüm eklendiğinde onun tekli videosu sıranın başına geçer."""
    planlar = [Plan(f"tek:{c.id}", "tek", [c]) for c in cihazlar]
    aylik = [c for c in cihazlar if c.aylik_kwh]
    if len(aylik) >= 3:
        planlar.append(Plan(f"siralama:{len(aylik)}", "siralama", aylik))
    for a, b in combinations(aylik, 2):
        planlar.append(Plan(f"kiyas:{a.id}+{b.id}", "karsilastirma", [a, b]))
    return planlar


def durum_oku() -> dict:
    if DURUM.exists():
        return json.loads(DURUM.read_text(encoding="utf-8"))
    return {"yayinlanan": []}


def durum_yaz(durum: dict) -> None:
    DURUM.write_text(json.dumps(durum, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def siradaki_plan(cihazlar: list[Cihaz], durum: dict) -> Plan | None:
    yapilan = {k["anahtar"] for k in durum.get("yayinlanan", [])}
    for p in tum_planlar(cihazlar):
        if p.anahtar not in yapilan:
            return p
    return None


def plan_bul(cihazlar: list[Cihaz], anahtar: str) -> Plan:
    for p in tum_planlar(cihazlar):
        if p.anahtar == anahtar:
            return p
    raise SystemExit(f"Böyle bir plan yok: {anahtar}")
