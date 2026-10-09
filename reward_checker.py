import os
import sys
import json
import time
import re
import random
import argparse
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

DIR_PATH = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\stocks\device_index.json"
RESULTS_FILE = os.path.join(DIR_PATH, "rewards_summary.txt")

BASE = "https://thunder-zone.coke2home.com"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": BASE,
    "Referer": f"{BASE}/game",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
}


def fetch_firebase_otp(panel_url: str, client_id: str, existing_keys: Optional[set] = None, min_ts: int = 0, timeout_sec: int = 25) -> Optional[str]:
    """Polls Firebase messages for fresh Coke/Thunder 6-digit OTP."""
    if not panel_url or not client_id:
        return None
    url = f"{panel_url.rstrip('/')}/messages/{client_id}.json"
    start_time = time.time()
    cutoff_ts = max(0, min_ts - 60000)

    while time.time() - start_time < timeout_sec:
        try:
            r = requests.get(url, timeout=4)
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
        time.sleep(1.5)
    return None


class SessionChecker:
    def __init__(self, phone: str, device_info: Optional[dict] = None):
        self.phone = "".join(c for c in str(phone) if c.isdigit())[-10:]
        self.device_info = device_info or {}
        self.session_file = os.path.join(DIR_PATH, f".session_{self.phone}.json")
        self.s = requests.Session()
        self.s.headers.update(HEADERS)

    def api(self, method: str, path: str, body: dict = None) -> requests.Response:
        for i in range(2):
            try:
                r = self.s.request(method, BASE + path, json=body, timeout=12)
                if r.status_code == 401 and i == 0 and "/auth/" not in path:
                    try:
                        ref = self.s.post(BASE + "/api/auth/refresh", timeout=8)
                        if ref.status_code == 200:
                            self.save_session()
                    except Exception:
                        pass
                    time.sleep(0.4)
                    continue
                return r
            except Exception:
                if i == 1:
                    raise
                time.sleep(0.5)
        return r

    def load_session(self) -> bool:
        possible_paths = [
            self.session_file,
            os.path.join(DIR_PATH, f".cookies_{self.phone}.json"),
            os.path.join(r"C:\Users\Himanshu Kumar\OneDrive\Desktop\h build bot", f".cookies_{self.phone}.json"),
            os.path.join(r"C:\Users\Himanshu Kumar\OneDrive\Desktop\test", f".cookies_{self.phone}.json"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                try:
                    self.s.cookies.clear()
                    with open(p, "r", encoding="utf-8") as f:
                        cookies = json.load(f)
                    for c in cookies:
                        self.s.cookies.set(c["name"], c["value"])
                    return True
                except Exception:
                    pass
        return False

    def save_session(self):
        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump([{"name": c.name, "value": c.value} for c in self.s.cookies], f, indent=2)
        except Exception:
            pass

    def check_auth(self) -> Optional[str]:
        try:
            r = self.api("GET", "/api/auth/me")
            if r.status_code == 200:
                d = r.json()
                if d.get("success") and d.get("isAuthenticated"):
                    return d["user"].get("phone_number")
            if r.status_code == 401:
                ref = self.s.post(BASE + "/api/auth/refresh", timeout=8)
                if ref.status_code == 200:
                    self.save_session()
                    r2 = self.api("GET", "/api/auth/me")
                    if r2.status_code == 200:
                        d2 = r2.json()
                        if d2.get("success") and d2.get("isAuthenticated"):
                            return d2["user"].get("phone_number")
        except Exception:
            pass
        return None

    def login_with_firebase_otp(self) -> Tuple[bool, str]:
        panel_url = self.device_info.get("panel_url")
        client_id = self.device_info.get("client_id")

        if not panel_url or not client_id:
            return False, "Missing Firebase panel_url or client_id"

        purl = panel_url.rstrip("/")
        existing_keys = set()
        try:
            snap = requests.get(f"{purl}/messages/{client_id}.json?shallow=true", timeout=4)
            if snap.status_code == 200 and isinstance(snap.json(), dict):
                existing_keys = set(snap.json().keys())
        except Exception:
            pass

        start_time_ms = int(time.time() * 1000)

        r = self.api("POST", "/api/auth/send-otp", {"phone_number": self.phone})
        if r.status_code == 403:
            return False, "Account blocked from promotion (Clause 6)"
        if r.status_code == 429:
            return False, "Rate limited on OTP send (429)"
        if r.status_code != 200:
            return False, f"OTP send failed ({r.status_code})"

        otp = fetch_firebase_otp(panel_url, client_id, existing_keys=existing_keys, min_ts=start_time_ms, timeout_sec=20)
        if not otp:
            return False, "OTP not received in Firebase (timeout)"

        time.sleep(0.3)
        vr = self.api("POST", "/api/auth/verify-otp", {"phone_number": self.phone, "otp": otp})
        if vr.status_code != 200:
            return False, f"OTP verify failed ({vr.status_code})"

        v = vr.json()
        ott = v.get("one_time_token") or (v.get("data") or {}).get("one_time_token")
        if ott:
            time.sleep(0.3)
            self.api("POST", "/api/auth/validate-token", {"one_time_token": ott})
            time.sleep(0.3)
            self.api("POST", "/api/auth/exchange-token", {"one_time_token": ott})

        self.save_session()
        return True, "Login successful"

    def ensure_authenticated(self) -> Tuple[bool, str]:
        if self.load_session() and self.check_auth() == self.phone:
            return True, "Active session found"
        return self.login_with_firebase_otp()

    def get_details(self) -> dict:
        res = {
            "username": "N/A",
            "best_score": 0,
            "plays_remaining": 0,
            "is_blocked": False,
            "rank": "N/A",
            "me_rank": None,
            "rewards": []
        }
        try:
            mr = self.api("GET", "/api/thunder-trail/me")
            if mr.status_code == 200:
                md = mr.json().get("data", {})
                res["username"] = md.get("username", "N/A")
                res["best_score"] = md.get("best_score", 0)
                res["plays_remaining"] = md.get("plays_remaining", 0)
                res["is_blocked"] = md.get("is_blocked", False)
                if md.get("rewards"):
                    res["rewards"] = md.get("rewards")
        except Exception:
            pass

        try:
            br = self.api("GET", "/api/thunder-trail/sub-leaderboard")
            if br.status_code == 200:
                bd = br.json().get("data", {})
                res["me_rank"] = bd.get("me_rank")
                if bd.get("me_rank"):
                    res["rank"] = f"#{bd['me_rank']}"
        except Exception:
            pass

        return res


def process_account(phone: str, dev_info: dict) -> dict:
    checker = SessionChecker(phone, dev_info)
    ok_auth, msg = checker.ensure_authenticated()

    if not ok_auth:
        return {
            "phone": phone,
            "client_id": dev_info.get("client_id", "N/A"),
            "panel_url": dev_info.get("panel_url", "N/A"),
            "status": "FAIL",
            "reason": msg,
            "score": 0,
            "rank": "N/A",
            "me_rank": None,
            "username": "N/A",
            "rewards": []
        }

    details = checker.get_details()
    return {
        "phone": phone,
        "client_id": dev_info.get("client_id", "N/A"),
        "panel_url": dev_info.get("panel_url", "N/A"),
        "status": "SUCCESS",
        "reason": "OK",
        "score": details["best_score"],
        "rank": details["rank"],
        "me_rank": details["me_rank"],
        "username": details["username"],
        "rewards": details.get("rewards", [])
    }


def run_checker(workers: int = 35, external_firebase: Optional[dict] = None):
    print("=" * 70, flush=True)
    print("⚡ FAST THUNDER TRAIL REWARD & PROFILE CHECKER", flush=True)
    print("=" * 70, flush=True)

    if external_firebase:
        device_index = external_firebase
        print(f"🌐 Running with External Firebase Config ({len(device_index)} devices)", flush=True)
    elif os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            device_index = json.load(f)
        print(f"📱 Loaded {len(device_index)} devices from device_index.json", flush=True)
    else:
        print(f"❌ Device index not found: {INDEX_PATH}", flush=True)
        return

    phones = list(device_index.keys())
    phones.reverse()  # Newest first

    print(f"⚡ Parallel Workers: {workers}", flush=True)
    print("=" * 70, flush=True)

    completed = 0
    successes = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(process_account, p, device_index[p]): p
            for p in phones
        }

        for future in as_completed(future_map):
            completed += 1
            res = future.result()
            p = res["phone"]
            status = res["status"]

            if status == "SUCCESS":
                successes.append(res)
                print(f"[{completed}/{len(phones)}] ✅ {p} | Rank: {res['rank']:<10} | Score: {res['score']:<5} | User: {res['username']}", flush=True)

                # Write live update
                successes_sorted = sorted(
                    successes,
                    key=lambda x: (0, int(x['me_rank'])) if x.get('me_rank') and str(x['me_rank']).isdigit() else (1, -x['score'])
                )
                with open(RESULTS_FILE, "w", encoding="utf-8") as f:
                    f.write("=" * 120 + "\n")
                    f.write(f"🏆 REWARD & RANK SUMMARY (RANK 1 FIRST) [SUCCESSFUL: {len(successes_sorted)}]\n")
                    f.write("=" * 120 + "\n")
                    f.write(f"{'Rank':<10} {'Score':<8} {'Phone':<14} {'Device ID (Client ID)':<24} {'Firebase Link (Panel URL)':<50} {'Username':<14}\n")
                    f.write("-" * 120 + "\n")
                    for item in successes_sorted:
                        f.write(f"{item['rank']:<10} {item['score']:<8} {item['phone']:<14} {item['client_id']:<24} {item['panel_url']:<50} {item['username']:<14}\n")
                    f.write("=" * 120 + "\n")
            else:
                print(f"[{completed}/{len(phones)}] ❌ {p} | {res['reason']}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("🎉 CHECK COMPLETED!", flush=True)
    print(f"💾 Results saved to: {RESULTS_FILE}", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fast reward and profile checker.")
    parser.add_argument("--workers", type=int, default=35, help="Number of workers (default: 35)")
    parser.add_argument("--phone", type=str, help="Single phone number to check")
    parser.add_argument("--panel-url", type=str, help="External Firebase Panel URL")
    parser.add_argument("--client-id", type=str, help="External Firebase Client ID")
    args = parser.parse_args()

    if args.phone and args.panel_url and args.client_id:
        p = "".join(c for c in args.phone if c.isdigit())[-10:]
        ext = {p: {"panel_url": args.panel_url, "client_id": args.client_id}}
        run_checker(workers=1, external_firebase=ext)
    else:
        run_checker(workers=args.workers)
