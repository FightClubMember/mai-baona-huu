import requests, re, os, sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

BASE = "https://thunder-zone.coke2home.com"
headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"}

# Fetch the JS chunks
chunks = [
    "/_next/static/chunks/3j-84hlbcq1wo.js",
    "/_next/static/chunks/0vzuv7gvwt3qm.js",
    "/_next/static/chunks/0eous8iilairc.js",
    "/_next/static/chunks/44kw6_zn8mxd7.js",
    "/_next/static/chunks/2iprnspzp3xfm.js",
    "/_next/static/chunks/44ohy06m7ygm-.js",
    "/_next/static/chunks/3kg-i7a_08uf_.js",
    "/_next/static/chunks/2-soe6ohulry3.js",
    "/_next/static/chunks/0cz1d0mv5g_q7.js",
    "/_next/static/chunks/21iry_25cpmlq.js",
    "/_next/static/chunks/turbopack-2xcltf1c7ca2f.js",
    "/_next/static/chunks/2ywaesjr_v25c.js",
    "/_next/static/chunks/396mtptnw5lal.js",
    "/_next/static/chunks/0al3_g0f943vi.js"
]

for c in chunks:
    try:
        r = requests.get(BASE + c, headers=headers)
        if r.status_code == 200:
            text = r.text
            # Look for all other chunks imported via turbopack or dynamic import
            sub = re.findall(r'static\/chunks\/[a-zA-Z0-9_\-\.]+\.js', text)
            if sub:
                print(f"{c} references {len(sub)} other chunks: {set(sub)}")
            
            # Check for api routes
            apis = re.findall(r'\/api\/[a-zA-Z0-9_\-\/]+', text)
            if apis:
                unique_apis = set(apis)
                tt_apis = [a for a in unique_apis if "thunder" in a or "auth" in a or "game" in a or "trail" in a]
                if tt_apis:
                    print(f"APIs in {c}: {tt_apis}")
    except Exception as e:
        print(f"Error {c}: {e}")
