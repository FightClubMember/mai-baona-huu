"""
find_live_firebase_panels.py — Scan device_index.json for active Firebase SMS panels receiving messages today
"""
import json, os, random, requests, sys, time

DEV_INDEX = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\stocks\device_index.json"
HERE = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (2)"

devices = json.load(open(DEV_INDEX))
keys = list(devices.keys())
random.shuffle(keys)

print(f"Loaded {len(keys)} total devices from device_index.json")
print("Scanning Firebase panels for active SMS messages received today...\n")

live_panels = []

for phone in keys[:200]:
    info = devices[phone]
    purl = info.get("panel_url", "").rstrip("/")
    cid = info.get("client_id", "")
    if not purl or not cid: continue

    sms_url = f"{purl}/clients/{cid}/sms.json"
    try:
        r = requests.get(sms_url, timeout=3)
        if r.status_code == 200 and r.json():
            data = r.json()
            # Check if data contains SMS messages
            count = len(data) if isinstance(data, dict) else 0
            if count > 0:
                print(f"🔥 LIVE FIREBASE PANEL FOUND: Mobile={phone} | ClientID={cid} | Messages={count}")
                live_panels.append({"phone": phone, "panel_url": purl, "client_id": cid, "msg_count": count})
    except Exception:
        pass

print(f"\n==========================================================")
print(f"  TOTAL LIVE SMS PANELS FOUND: {len(live_panels)}")
print(f"==========================================================")

if live_panels:
    json.dump(live_panels, open(os.path.join(HERE, "live_firebase_panels.json"), "w"), indent=2)
    print(f"Saved {len(live_panels)} live panels to live_firebase_panels.json")
