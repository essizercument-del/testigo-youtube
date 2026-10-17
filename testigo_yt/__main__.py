"""Kullanım:
  python -m testigo_yt --liste                 # planlanan videolar ve durumları
  python -m testigo_yt                         # sıradaki videoyu üret (yüklemez)
  python -m testigo_yt --plan tek:buzdolabi    # belirli bir videoyu üret
  python -m testigo_yt --yukle                 # sıradakini üret + YouTube'a yükle + durum.json güncelle
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

from . import veri
from .metin import meta_olustur
from .sahneler import sahneleri_kur
from .video import videoyu_uret

CIKTI = veri.KOK / "out"


def _dosya_adi(anahtar: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", anahtar.lower()).strip("-")


def _github_ozet(satirlar: list[str]):
    yol = os.environ.get("GITHUB_STEP_SUMMARY")
    if yol:
        with open(yol, "a", encoding="utf-8") as f:
            f.write("\n".join(satirlar) + "\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="testigo_yt")
    ap.add_argument("--liste", action="store_true")
    ap.add_argument("--plan", help="belirli plan anahtarı (bkz. --liste)")
    ap.add_argument("--yukle", action="store_true", help="YouTube'a yükle ve durumu kaydet")
    ap.add_argument("--gizlilik", choices=["private", "unlisted", "public"])
    ap.add_argument("--onizleme", action="store_true", help="her sahneden bir JPG kare kaydet")
    a = ap.parse_args(argv)

    ayar = veri.ayar_yukle()
    cihazlar = veri.cihazlari_yukle(ayar)
    durum = veri.durum_oku()
    yapilan = {k["anahtar"]: k for k in durum["yayinlanan"]}

    if a.liste:
        for p in veri.tum_planlar(cihazlar):
            k = yapilan.get(p.anahtar)
            isaret = f"✓ {k['tarih']} {k.get('video_id', '')}" if k else "·"
            print(f"{isaret:28} {p.anahtar}")
        return 0

    bugun = dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).strftime("%Y-%m-%d")
    if a.yukle and not a.plan and os.environ.get("GITHUB_EVENT_NAME") == "schedule" and any(
            k["tarih"].startswith(bugun) for k in durum["yayinlanan"]):
        print("Bugün zaten bir video yüklendi, zamanlanmış çalışma atlanıyor.")
        return 0

    plan = veri.plan_bul(cihazlar, a.plan) if a.plan else veri.siradaki_plan(cihazlar, durum)
    if plan is None:
        msg = "Yeni video kalmadı: data/olcumler.json'a yeni ölçüm ekle."
        print(msg)
        _github_ozet([f"⚠️ {msg}"])
        return 3 if a.yukle else 0

    ad = _dosya_adi(plan.anahtar)
    mp4 = CIKTI / f"{ad}.mp4"
    meta = meta_olustur(plan, ayar)
    print(f"Plan: {plan.anahtar}\nBaşlık: {meta['baslik']}")
    sahneler = sahneleri_kur(plan, cihazlar, ayar, ayar["video"]["fps"])
    videoyu_uret(sahneler, ayar, mp4, tohum=plan.anahtar,
                 onizleme_dir=(CIKTI / f"{ad}_kareler") if a.onizleme else None)
    (CIKTI / f"{ad}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Video: {mp4} ({mp4.stat().st_size / 1e6:.1f} MB, {sum(s.sure for s in sahneler):.1f} sn)")

    if not a.yukle:
        return 0

    from .yukle import yukle  # google kütüphaneleri yalnızca yüklemede gerekli
    gizlilik = a.gizlilik or ayar["yukleme"]["gizlilik"]
    vid = yukle(mp4, meta, ayar, gizlilik)
    url = f"https://youtube.com/shorts/{vid}"
    print(f"Yüklendi: {url} ({gizlilik})")
    durum["yayinlanan"].append({
        "anahtar": plan.anahtar,
        "video_id": vid,
        "tarih": dt.datetime.now(dt.timezone(dt.timedelta(hours=3))).strftime("%Y-%m-%d %H:%M"),
        "baslik": meta["baslik"],
        "gizlilik": gizlilik,
    })
    veri.durum_yaz(durum)
    _github_ozet([f"### ✅ {meta['baslik']}", f"- Video: {url}", f"- Gizlilik: `{gizlilik}`",
                  f"- Plan: `{plan.anahtar}`"])
    return 0


def _gh_hata(mesaj: str):
    """Hata mesajını GitHub Actions özetine ve annotation'a yazar."""
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    kacis = mesaj.replace("%", "%25").replace("\r", "").replace("\n", "%0A")
    print(f"::error title=Video hatası::{kacis[:3000]}", flush=True)
    _github_ozet(["### ❌ Hata", "```", mesaj[-6000:], "```"])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as e:
        if isinstance(e.code, str):
            _gh_hata(e.code)
            print(e.code, file=sys.stderr)
            sys.exit(1)
        raise
    except Exception:  # noqa: BLE001
        import traceback
        iz = traceback.format_exc()
        print(iz, file=sys.stderr)
        _gh_hata(iz)
        sys.exit(1)
