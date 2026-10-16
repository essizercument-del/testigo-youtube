"""
Testigo YouTube - tek seferlik yetkilendirme
---------------------------------------------
Kullanım:
  1) Bu dosyayı ve indirdiğin client_secret...json dosyasını aynı klasöre koy
  2) pip install google-auth-oauthlib google-api-python-client
  3) python get_token.py

Tarayıcı açılır, kanal hesabınla izin verirsin. Sonunda GitHub Secrets'a
eklenecek 3 değer ekrana yazdırılır. Bu değerleri kimseyle paylaşma.
"""
import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",    # video yükleme
    "https://www.googleapis.com/auth/youtube.readonly",  # kanal adını doğrulamak için
]

HERE = Path(__file__).resolve().parent


def find_secret_file() -> Path:
    exact = HERE / "client_secret.json"
    if exact.exists():
        return exact
    candidates = sorted(HERE.glob("client_secret*.json"))
    if not candidates:
        print("HATA: Bu klasörde client_secret*.json bulunamadı.")
        print(f"Klasör: {HERE}")
        sys.exit(1)
    return candidates[0]


def main() -> None:
    secret_path = find_secret_file()
    print(f"Kullanılan anahtar dosyası: {secret_path.name}")

    flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
    creds = flow.run_local_server(
        port=0,
        prompt="consent",        # refresh token'ın kesin gelmesi için
        access_type="offline",
        authorization_prompt_message="Tarayıcı açılıyor, kanal hesabınla giriş yap...",
        success_message="Yetkilendirme tamam. Bu sekmeyi kapatıp terminale dönebilirsin.",
    )

    if not creds.refresh_token:
        print("HATA: refresh token alınamadı. myaccount.google.com/permissions adresinden")
        print("'Testigo Uploader' iznini kaldırıp script'i tekrar çalıştır.")
        sys.exit(1)

    # Doğru kanala bağlandığımızı kontrol et
    youtube = build("youtube", "v3", credentials=creds)
    resp = youtube.channels().list(part="snippet", mine=True).execute()
    items = resp.get("items", [])
    channel = items[0]["snippet"]["title"] if items else None

    data = json.loads(secret_path.read_text(encoding="utf-8"))
    info = data.get("installed") or data.get("web") or {}

    print()
    print("=" * 60)
    if channel:
        print(f"Bağlanan kanal: {channel}")
    else:
        print("UYARI: Bu hesapta YouTube kanalı bulunamadı.")
        print("Girişte kanalın bağlı olduğu hesabı/marka hesabını seçtiğinden emin ol.")
    print("=" * 60)
    print("GitHub Secrets'a eklenecek değerler:\n")
    print(f"YT_CLIENT_ID      = {info.get('client_id')}")
    print(f"YT_CLIENT_SECRET  = {info.get('client_secret')}")
    print(f"YT_REFRESH_TOKEN  = {creds.refresh_token}")
    print()
    print("Bu değerleri sohbete veya herkese açık bir yere yapıştırma.")
    print("=" * 60)


if __name__ == "__main__":
    main()
