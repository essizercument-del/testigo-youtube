import json, os, re, requests
S = requests.Session(); S.headers["User-Agent"] = "Mozilla/5.0 (testigo-youtube; site sahibi)"
B = "https://testigotr.com.tr/wp-json/wp/v2"
def all_pages(ep, fields):
    out, p = [], 1
    while True:
        r = S.get(f"{B}/{ep}", params={"per_page": 100, "page": p, "_fields": fields}, timeout=30)
        print(ep, p, r.status_code)
        if r.status_code != 200: break
        d = r.json(); out += d
        if len(d) < 100: break
        p += 1
    return out
posts = all_pages("posts", "id,slug,title,link,featured_media")
media = all_pages("media", "id,post,source_url,alt_text,mime_type,media_details")
slug = {p["id"]: p["slug"] for p in posts}
os.makedirs("gorsel_deneme/indir", exist_ok=True)
idx = []
for m in media:
    if not m.get("mime_type", "").startswith("image"): continue
    sizes = (m.get("media_details") or {}).get("sizes") or {}
    url = (sizes.get("large") or sizes.get("full") or {}).get("source_url") or m["source_url"]
    folder = slug.get(m.get("post"), "_ekli_degil")
    os.makedirs(f"gorsel_deneme/indir/{folder}", exist_ok=True)
    fn = f"gorsel_deneme/indir/{folder}/{m['id']}_" + re.sub(r"[^\w.-]", "_", url.split("/")[-1])[-60:]
    try:
        r = S.get(url, timeout=60)
        if r.ok: open(fn, "wb").write(r.content); idx.append({"dosya": fn, "post": folder, "alt": m.get("alt_text"), "url": url})
    except Exception as e: print("hata", url, e)
json.dump({"posts": posts, "gorseller": idx}, open("gorsel_deneme/indir/index.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(posts), "yazı,", len(idx), "görsel")
