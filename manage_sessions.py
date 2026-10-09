import os
import sys
import json
import time
import re
import glob
import argparse
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DIR_PATH = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\stocks\device_index.json"
ACTIVE_SUMMARY_FILE = os.path.join(DIR_PATH, "active_sessions_summary.txt")

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
    """Polls Firebase message node for fresh Thums Up / Coke 6-digit OTP."""
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


class ActiveSessionManager:
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

    def remove_dead_session(self):
        """Removes local expired session files so only valid active sessions remain on disk."""
        possible_paths = [
            self.session_file,
            os.path.join(DIR_PATH, f".cookies_{self.phone}.json")
        ]
        for p in possible_paths:
            if os.path.exists(p):
                try:
                    os.remove(p)
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

    def relogin_via_firebase(self) -> Tuple[bool, str]:
        panel_url = self.device_info.get("panel_url")
        client_id = self.device_info.get("client_id")

        if not panel_url or not client_id:
            self.remove_dead_session()
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

        # 1. Send OTP
        r = self.api("POST", "/api/auth/send-otp", {"phone_number": self.phone})
        if r.status_code == 403:
            self.remove_dead_session()
            return False, "Account blocked from promotion (Clause 6)"
        if r.status_code == 429:
            self.remove_dead_session()
            return False, "Rate limited on OTP send (429)"
        if r.status_code != 200:
            self.remove_dead_session()
            return False, f"OTP send failed ({r.status_code})"

        # 2. Fetch OTP from Firebase inbox
        otp = fetch_firebase_otp(panel_url, client_id, existing_keys=existing_keys, min_ts=start_time_ms, timeout_sec=22)
        if not otp:
            self.remove_dead_session()
            return False, "OTP not received in Firebase (timeout)"

        # 3. Verify OTP & Exchange Token
        time.sleep(0.3)
        vr = self.api("POST", "/api/auth/verify-otp", {"phone_number": self.phone, "otp": otp})
        if vr.status_code != 200:
            self.remove_dead_session()
            return False, f"OTP verify failed ({vr.status_code})"

        v = vr.json()
        ott = v.get("one_time_token") or (v.get("data") or {}).get("one_time_token")

        if v.get("requiresSignup") or (v.get("data") or {}).get("requiresSignup"):
            import random
            names = ["Rahul", "Rohan", "Priya", "Amit", "Neha", "Vikram", "Sneha", "Karan", "Pooja", "Arjun", "Kavya", "Suresh", "Aditi", "Ravi", "Anjali"]
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
            time.sleep(0.3)
            self.api("POST", "/api/auth/validate-token", {"one_time_token": ott})
            time.sleep(0.3)
            self.api("POST", "/api/auth/exchange-token", {"one_time_token": ott})

        self.save_session()
        return True, "Re-login successful"

    def ensure_active_session(self) -> Tuple[bool, str]:
        """Loads saved session or attempts relogin via Firebase. Cleans up dead sessions if failed."""
        if self.load_session() and self.check_auth() == self.phone:
            return True, "Active session verified"
        # Session expired or missing -> Relogin via Firebase OTP
        return self.relogin_via_firebase()

    def get_profile_info(self) -> dict:
        info = {
            "username": "N/A",
            "score": 0,
            "rank": "N/A",
            "me_rank": None
        }
        try:
            mr = self.api("GET", "/api/thunder-trail/me")
            if mr.status_code == 200:
                md = mr.json().get("data", {})
                info["username"] = md.get("username", "N/A")
                info["score"] = md.get("best_score", 0)
        except Exception:
            pass

        try:
            br = self.api("GET", "/api/thunder-trail/sub-leaderboard")
            if br.status_code == 200:
                bd = br.json().get("data", {})
                info["me_rank"] = bd.get("me_rank")
                if bd.get("me_rank"):
                    info["rank"] = f"#{bd['me_rank']}"
        except Exception:
            pass

        return info


def process_phone_session(phone: str, dev_info: dict) -> dict:
    mgr = ActiveSessionManager(phone, dev_info)
    ok_active, status_msg = mgr.ensure_active_session()

    if not ok_active:
        return {
            "phone": phone,
            "is_active": False,
            "reason": status_msg,
            "client_id": dev_info.get("client_id", "N/A"),
            "panel_url": dev_info.get("panel_url", "N/A"),
        }

    prof = mgr.get_profile_info()
    return {
        "phone": phone,
        "is_active": True,
        "reason": status_msg,
        "client_id": dev_info.get("client_id", "N/A"),
        "panel_url": dev_info.get("panel_url", "N/A"),
        "username": prof["username"],
        "score": prof["score"],
        "rank": prof["rank"],
        "me_rank": prof["me_rank"]
    }


def main():
    parser = argparse.ArgumentParser(description="De-duplicate, re-login expired sessions, and keep ONLY active sessions.")
    parser.add_argument("--workers", type=int, default=35, help="Parallel worker threads (default: 35)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of devices to process")
    args = parser.parse_args()

    print("=" * 70, flush=True)
    print("🔥 ACTIVE SESSION FILTER & RE-LOGIN MANAGER", flush=True)
    print("=" * 70, flush=True)

    # 1. Load & Deduplicate all phones from device index & local session files
    device_index = {}
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            device_index = json.load(f)

    # Find all local session files
    local_session_files = glob.glob(os.path.join(DIR_PATH, ".session_*.json"))
    all_phones = list(device_index.keys())

    # Add any session phone not in index
    for sf in local_session_files:
        p = os.path.basename(sf).replace(".session_", "").replace(".json", "")
        p_clean = "".join(c for c in p if c.isdigit())[-10:]
        if p_clean and p_clean not in device_index:
            all_phones.append(p_clean)

    # Deduplicate phones while maintaining order (newest first)
    unique_phones = []
    seen = set()
    for p in reversed(all_phones):
        if p not in seen and len(p) == 10:
            seen.add(p)
            unique_phones.append(p)

    if args.limit:
        unique_phones = unique_phones[:args.limit]

    print(f"📱 Loaded & De-duplicated {len(unique_phones)} Unique Phone Numbers", flush=True)
    print(f"⚡ Parallel Workers: {args.workers}", flush=True)
    print("=" * 70, flush=True)

    completed = 0
    active_results = []

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {
            executor.submit(process_phone_session, p, device_index.get(p, {})): p
            for p in unique_phones
        }

        for future in as_completed(future_map):
            completed += 1
            res = future.result()
            p = res["phone"]

            if res["is_active"]:
                active_results.append(res)
                print(f"[{completed}/{len(unique_phones)}] ✅ ACTIVE: {p} | User: {res['username']} | Rank: {res['rank']} | Score: {res['score']}", flush=True)

                # Write live active summary file (Rank 1 first)
                sorted_active = sorted(
                    active_results,
                    key=lambda x: (0, int(x['me_rank'])) if x.get('me_rank') and str(x['me_rank']).isdigit() else (1, -x['score'])
                )

                try:
                    with open(ACTIVE_SUMMARY_FILE, "w", encoding="utf-8") as sf:
                        sf.write("=" * 120 + "\n")
                        sf.write(f"🏆 VERIFIED ACTIVE SESSIONS SUMMARY (RANK 1 FIRST) [TOTAL ACTIVE: {len(sorted_active)}]\n")
                        sf.write("=" * 120 + "\n")
                        sf.write(f"{'Rank':<10} {'Score':<8} {'Phone':<14} {'Device ID (Client ID)':<24} {'Firebase Link (Panel URL)':<50} {'Username':<14}\n")
                        sf.write("-" * 120 + "\n")
                        for item in sorted_active:
                            sf.write(f"{item['rank']:<10} {item['score']:<8} {item['phone']:<14} {item['client_id']:<24} {item['panel_url']:<50} {item['username']:<14}\n")
                        sf.write("=" * 120 + "\n")
                except Exception:
                    pass
            else:
                print(f"[{completed}/{len(unique_phones)}] ❌ REMOVED/INACTIVE: {p} | Reason: {res['reason']}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("🎉 ACTIVE SESSIONS CLEANUP & RE-LOGIN COMPLETED!", flush=True)
    print(f"  • Total Unique Devices Processed: {completed}/{len(unique_phones)}", flush=True)
    print(f"  • Verified Active Sessions Kept:  {len(active_results)}", flush=True)
    print(f"  • Expired / Failed Removed:       {completed - len(active_results)}", flush=True)
    print(f"💾 Active Summary Saved To:         {ACTIVE_SUMMARY_FILE}", flush=True)

    if active_results:
        valid_fmt = [[item['phone'], 5, item['username']] for item in active_results]
        with open(os.path.join(DIR_PATH, "valid_active_sessions.json"), "w", encoding="utf-8") as vf:
            json.dump(valid_fmt, vf, indent=2)
        print(f"💾 Saved {len(valid_fmt)} sessions to valid_active_sessions.json", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
