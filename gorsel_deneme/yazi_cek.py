import json, re, html, requests, ssl, socket, subprocess, certifi
def tam_zincir(host="testigotr.com.tr"):
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, 443), timeout=20) as so, ctx.wrap_socket(so, server_hostname=host) as ss:
        der = ss.getpeercert(binary_form=True)
    leaf = ssl.DER_cert_to_PEM_cert(der)
    txt = subprocess.run(["openssl", "x509", "-noout", "-text"], input=leaf, capture_output=True, text=True).stdout
    print([l.strip() for l in txt.splitlines() if "Issuer:" in l or "CA Issuers" in l])
    eklenen = ""
    for _ in range(4):
        m = re.search(r"CA Issuers - URI:(\S+)", txt)
        if not m: break
        ara = requests.get(m.group(1), timeout=30).content
        pem = subprocess.run(["openssl", "x509", "-inform", "PEM" if ara.startswith(b"-----") else "DER"], input=ara, capture_output=True).stdout.decode()
        eklenen += pem + "\n"
        txt = subprocess.run(["openssl", "x509", "-noout", "-text"], input=pem, capture_output=True, text=True).stdout
        print([l.strip() for l in txt.splitlines() if "Issuer:" in l or "Subject:" in l or "CA Issuers" in l])
    open("zincir.pem", "w").write(open(certifi.where()).read() + "\n" + eklenen)
    return "zincir.pem"

S = requests.Session(); S.verify = tam_zincir(); S.headers["User-Agent"] = "Mozilla/5.0 (testigo-youtube; site sahibi)"
slugs = ["isi-pompali-kurutma-makinesi-elektrik-tuketimi"]
out = {}
for s in slugs:
    r = S.get("https://testigotr.com.tr/wp-json/wp/v2/posts", params={"slug": s, "_fields": "title,content,link"}, timeout=30)
    p = r.json()[0]
    t = re.sub(r"<(script|style)[^>]*>.*?</\\1>", " ", p["content"]["rendered"], flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    t = re.sub(r"\n\s*\n+", "\n", t)
    out[s] = {"title": p["title"]["rendered"], "link": p["link"], "text": t}
json.dump(out, open("gorsel_deneme/yazilar.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok", {k: len(v["text"]) for k, v in out.items()})
