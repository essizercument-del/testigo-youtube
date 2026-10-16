"""YouTube Data API v3 ile video yükleme (refresh token ile, tarayıcısız)."""
from __future__ import annotations

import os
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]


def _kimlik() -> Credentials:
    eksik = [k for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN") if not os.environ.get(k)]
    if eksik:
        raise SystemExit(f"Eksik ortam değişkeni / GitHub Secret: {', '.join(eksik)}")
    cr = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"].strip(),
        client_id=os.environ["YT_CLIENT_ID"].strip(),
        client_secret=os.environ["YT_CLIENT_SECRET"].strip(),
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    try:
        cr.refresh(Request())
    except Exception as e:  # noqa: BLE001
        raise SystemExit(
            "Google oturumu yenilenemedi. Refresh token süresi dolmuş olabilir "
            "(uygulama 'Test' modundaysa 7 günde bir dolar). get_token.py'yi tekrar çalıştırıp "
            f"YT_REFRESH_TOKEN secret'ını güncelle.\nAyrıntı: {e}") from e
    return cr


def yukle(video: Path, meta: dict, ayar: dict, gizlilik: str | None = None) -> str:
    y = ayar["yukleme"]
    youtube = build("youtube", "v3", credentials=_kimlik(), cache_discovery=False)
    govde = {
        "snippet": {
            "title": meta["baslik"],
            "description": meta["aciklama"],
            "tags": meta["etiketler"],
            "categoryId": y["kategori_id"],
            "defaultLanguage": y["dil"],
            "defaultAudioLanguage": y["dil"],
        },
        "status": {
            "privacyStatus": gizlilik or y["gizlilik"],
            "selfDeclaredMadeForKids": y["cocuklara_ozel"],
            "containsSyntheticMedia": False,
        },
    }
    medya = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    istek = youtube.videos().insert(part="snippet,status", body=govde, media_body=medya)
    yanit, deneme = None, 0
    while yanit is None:
        try:
            durum, yanit = istek.next_chunk()
            if durum:
                print(f"  yükleniyor: %{int(durum.progress() * 100)}")
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504) and deneme < 5:
                deneme += 1
                time.sleep(2 ** deneme)
                continue
            if e.resp.status == 403 and b"quota" in e.content.lower():
                raise SystemExit("YouTube API günlük kotası doldu, yarın tekrar denenecek.") from e
            raise
    return yanit["id"]
