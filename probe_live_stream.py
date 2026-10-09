import base64, hashlib, hmac, json, os, random, sys, time
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

BASE = "https://thunder-zone.coke2home.com"
HERE = os.path.dirname(os.path.abspath(__file__))

# Test on single test account (9653840303 - already flagged, safe to experiment)
TEST_PHONE = "9653840303"

s = requests.Session()
s.headers.update({
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": BASE,
    "Referer": f"{BASE}/game",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"
})

fpath = os.path.join(HERE, f".session_{TEST_PHONE}.json")
for c in json.load(open(fpath)):
    s.cookies.set(c["name"], c["value"])

print(f"1. Opening session on test account {TEST_PHONE}...")
r_sess = s.post(BASE + "/api/thunder-trail/sessions", json={}, timeout=10)
print(f"Session response ({r_sess.status_code}):\n{r_sess.text}\n")

if r_sess.status_code in (200, 201):
    sd = r_sess.json().get("data", {})
    sid = sd.get("session_id")
    token = sd.get("session_token")
    ticket = sd.get("socket_ticket")
    frame_key = sd.get("frame_key")
    
    print("Testing related endpoints with socket ticket / frame key:")
    for path in [
        f"/api/thunder-trail/sessions/{sid}/stream",
        f"/api/thunder-trail/sessions/{sid}/frames",
        f"/api/thunder-trail/sessions/{sid}/sync",
        f"/api/thunder-trail/sessions/{sid}/connect",
        f"/api/thunder-trail/sessions/{sid}/drip-refill"
    ]:
        for payload in [
            {"session_token": token, "socket_ticket": ticket, "frame_key": frame_key},
            {"session_token": token, "ticket": ticket},
            {"session_token": token}
        ]:
            try:
                test_r = s.post(BASE + path, json=payload, timeout=4)
                if test_r.status_code != 404:
                    print(f"🔥 [{path}] Status {test_r.status_code}: {test_r.text[:150]}")
            except Exception:
                pass
