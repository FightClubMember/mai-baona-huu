import requests, re

BASE = "https://thunder-zone.coke2home.com"
headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"}

# Check Next.js build manifest
r = requests.get(BASE + "/_next/static/development/_buildManifest.js", headers=headers)
if r.status_code != 200:
    # Try finding build id in HTML
    r_home = requests.get(BASE + "/game", headers=headers)
    m = re.search(r'"buildId":"([^"]+)"', r_home.text)
    if m:
        build_id = m.group(1)
        print("Found buildId:", build_id)
        bm_url = f"{BASE}/_next/static/{build_id}/_buildManifest.js"
        r_bm = requests.get(bm_url, headers=headers)
        print(f"Build manifest ({bm_url}): {r_bm.status_code}")
        if r_bm.status_code == 200:
            chunks = re.findall(r'"static/chunks/[^"]+"', r_bm.text)
            print(f"Found {len(chunks)} chunks in manifest")
            for c in chunks:
                c_clean = c.strip('"')
                res = requests.get(f"{BASE}/_next/{c_clean}", headers=headers)
                if any(w in res.text for w in ["socket_ticket", "frame_key", "live_mode", "/api/thunder-trail/sessions"]):
                    print(f"🔥 KEY CHUNK: {c_clean}")
                    for k in ["socket_ticket", "frame_key", "live_mode", "/api/thunder-trail/sessions"]:
                        if k in res.text:
                            idx = res.text.find(k)
                            print(f"  [{k}]: {res.text[max(0, idx-100):min(len(res.text), idx+300)]}\n")
