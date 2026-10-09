"""
===================================================================================
THUNDER TRAIL AUTO / MANUAL SESSION EXTRACTOR & LEADERBOARD AUDITOR
-----------------------------------------------------------------------------------
CREATED WITH LOVE FOR HIMANSHU KUMAR BY ONYX v67
===================================================================================
"""

import glob
import json
import os
import re
import sys
import time
import winsound
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

# Terminal Color Codes & Styles
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

BASE_URL = "https://thunder-zone.coke2home.com"
HERE = os.path.dirname(os.path.abspath(__file__))
DEV_INDEX_PATH = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\stocks\device_index.json"

# Audio Celebrations using Custom MP3 files or Windows Synthesizer / Beep Frequencies
def play_audio_file(filename):
    """Plays an MP3 sound file asynchronously or in thread using Windows MCI API."""
    try:
        import ctypes
        filepath = os.path.join(HERE, filename)
        if os.path.exists(filepath):
            alias = f"mp3_{int(time.time() * 1000)}"
            ctypes.windll.winmm.mciSendStringW(f'open "{filepath}" type mpegvideo alias {alias}', None, 0, 0)
            ctypes.windll.winmm.mciSendStringW(f'play {alias}', None, 0, 0)
            return True
    except Exception:
        pass
    return False

def play_leaderboard_sound():
    """Celebration melody for Top 22 Leaderboard entry!"""
    # Try custom sound first
    sound_files = [f for f in os.listdir(HERE) if f.endswith(('.mp3', '.wav', '.m4a'))]
    if sound_files:
        # Prefer sigma or ladle mp3 if available
        target = sound_files[0]
        for f in sound_files:
            if "sigma" in f.lower() or "mka" in f.lower() or "meow" in f.lower():
                target = f
                break
        if play_audio_file(target):
            return

    try:
        notes = [(523, 120), (659, 120), (784, 150), (1046, 300)]
        for freq, dur in notes:
            winsound.Beep(freq, dur)
    except Exception:
        pass

def play_winner_sound():
    """Excited Fanfare melody for confirmed Winners with Prizes!"""
    sound_files = [f for f in os.listdir(HERE) if f.endswith(('.mp3', '.wav', '.m4a'))]
    if sound_files:
        target = sound_files[0]
        for f in sound_files:
            if "meow" in f.lower() or "mka" in f.lower() or "sigma" in f.lower():
                target = f
                break
        if play_audio_file(target):
            return

    try:
        fanfare = [
            (523, 100), (523, 100), (523, 100), (659, 250),
            (784, 250), (1046, 400), (880, 200), (1046, 600)
        ]
        for freq, dur in fanfare:
            winsound.Beep(freq, dur)
    except Exception:
        pass

def print_banner():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{CYAN}{BOLD}")
    print(r"  _____ _   _ _   _ _   _ ____  _____ ____    _____ ____    _    ___ _     ")
    print(r" |_   _| | | | | | | \ | |  _ \| ____|  _ \  |_   _|  _ \  / \  |_ _| |    ")
    print(r"   | | | |_| | | | |  \| | | | |  _| | |_) |   | | | |_) |/ _ \  | | |    ")
    print(r"   | | |  _  | |_| | |\  | |_| | |___|  _ <    | | |  _ </ ___ \ | | |___ ")
    print(r"   |_| |_| |_|\___/|_| \_|____/|_____|_| \_\   |_| |_| \_/_/   \_\___|_____|")
    print(f"{RESET}")
    print(f"{MAGENTA}{BOLD}==================================================================================={RESET}")
    print(f"{YELLOW}{BOLD}   [+] AUTOMATED SESSION EXTRACTOR & WINNER HARVESTER [+]{RESET}")
    print(f"{CYAN}   Designed with Craft & Precision for {BOLD}HIMANSHU KUMAR{RESET}")
    print(f"{MAGENTA}{BOLD}==================================================================================={RESET}\n")

def extract_sessions_from_text_files():
    """Auto-scans all .txt files in current directory to extract session cookies/tokens."""
    print(f"{BLUE}[*] Auto-Scanning directory for session .txt files...{RESET}")
    txt_files = glob.glob(os.path.join(HERE, "*.txt"))
    extracted_count = 0

    # Device index map for enrichment if available
    device_map = {}
    if os.path.exists(DEV_INDEX_PATH):
        try:
            device_map = json.load(open(DEV_INDEX_PATH, encoding="utf-8"))
        except Exception:
            pass

    for txt_file in txt_files:
        filename = os.path.basename(txt_file)
        if "summary" in filename or "results" in filename or "leaderboard" in filename:
            continue
        
        try:
            content = open(txt_file, encoding="utf-8", errors="ignore").read()
            phone_match = re.search(r'(?:91|0)?([6-9]\d{9})', content)
            phone = phone_match.group(1) if phone_match else None

            cookies = []
            try:
                json_data = json.loads(content)
                if isinstance(json_data, list):
                    cookies = json_data
                elif isinstance(json_data, dict):
                    if "cookies" in json_data:
                        cookies = json_data["cookies"]
                    elif "phone" in json_data:
                        phone = json_data["phone"]
            except Exception:
                cookie_matches = re.findall(r'(\b[\w\-.]+=[\w\-.]+)', content)
                for cm in cookie_matches:
                    if "=" in cm:
                        k, v = cm.split("=", 1)
                        cookies.append({"name": k, "value": v})

            if phone and cookies:
                target_path = os.path.join(HERE, f".session_{phone}.json")
                with open(target_path, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, indent=2)
                extracted_count += 1
                print(f"  {GREEN}[+] Extracted session file -> .session_{phone}.json{RESET}")
        except Exception:
            pass

    print(f"\n{GREEN}{BOLD}[+] Auto-Extraction Complete! Extracted {extracted_count} session files.{RESET}\n")

def audit_single_session(fpath, device_map):
    """Audits a single session for Leaderboard rank, Winner status, Rewards, and Firebase link."""
    phone = os.path.basename(fpath).replace(".session_", "").replace(".json", "")
    try:
        raw_cookies = json.load(open(fpath, encoding="utf-8"))
        if not raw_cookies:
            return None
        
        cookie_dict = {c["name"]: c["value"] for c in raw_cookies if isinstance(c, dict) and "name" in c and "value" in c}
        s = requests.Session()
        s.headers.update({
            "accept": "*/*",
            "content-type": "application/json",
            "origin": BASE_URL,
            "referer": f"{BASE_URL}/game",
            "user-agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"
        })
        for k, v in cookie_dict.items():
            s.cookies.set(k, v)

        # 1. Fetch /me info
        r = s.get(BASE_URL + "/api/thunder-trail/me", timeout=6)
        if r.status_code == 401:
            ref = s.post(BASE_URL + "/api/auth/refresh", timeout=6)
            if ref.status_code == 200:
                for c in s.cookies:
                    cookie_dict[c.name] = c.value
                json.dump([{"name": k, "value": v} for k, v in cookie_dict.items()], open(fpath, "w"), indent=2)
                r = s.get(BASE_URL + "/api/thunder-trail/me", timeout=6)

        if r.status_code != 200:
            return None

        me_data = r.json().get("data", {})
        username = me_data.get("username", "N/A")
        score = me_data.get("best_score", 0)
        rank = me_data.get("rank")
        is_winner = me_data.get("is_winner", False)
        plays_left = me_data.get("plays_remaining", 0)

        # 2. Fetch rewards if any
        rewards = []
        r_rew = s.get(BASE_URL + "/api/thunder-trail/my-rewards", timeout=6)
        if r_rew.status_code == 200:
            rewards = r_rew.json().get("data", {}).get("rewards", [])

        # Enrich with Device ID / Firebase Panel from index if present
        dev_info = device_map.get(phone, {})
        device_id = dev_info.get("client_id", "N/A")
        firebase_url = dev_info.get("panel_url", "N/A")

        return {
            "phone": phone,
            "username": username,
            "score": score,
            "rank": rank,
            "is_winner": is_winner,
            "plays_left": plays_left,
            "rewards": rewards,
            "device_id": device_id,
            "firebase_url": firebase_url
        }

    except Exception:
        return None

def run_auditor():
    session_files = sorted(glob.glob(os.path.join(HERE, ".session_*.json")))
    if not session_files:
        print(f"{RED}[!] No session files found to process.{RESET}")
        return

    print(f"{CYAN}{BOLD}[*] Auditing {len(session_files)} loaded sessions across endpoints...{RESET}\n")

    device_map = {}
    if os.path.exists(DEV_INDEX_PATH):
        try:
            device_map = json.load(open(DEV_INDEX_PATH, encoding="utf-8"))
        except Exception:
            pass

    leaderboard_under22 = []
    confirmed_winners = []

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(audit_single_session, f, device_map): f for f in session_files}
        for f in as_completed(futures):
            res = f.result()
            if not res:
                continue

            phone = res["phone"]
            uname = res["username"]
            score = res["score"]
            rank = res["rank"]
            is_win = res["is_winner"]
            rewards = res["rewards"]

            # Check if Winner
            if is_win or len(rewards) > 0:
                confirmed_winners.append(res)
                print(f"{YELLOW}{BOLD}[WINNER DETECTED] {phone} ({uname}) | Rank #{rank} | Rewards: {len(rewards)}{RESET}")
                play_winner_sound()

            # Check if Leaderboard Top 22
            elif rank is not None and isinstance(rank, int) and rank <= 22:
                leaderboard_under22.append(res)
                print(f"{GREEN}{BOLD}[TOP 22 LEADERBOARD] {phone} ({uname}) | Rank #{rank} | Score: {score}{RESET}")
                play_leaderboard_sound()
            else:
                print(f"{CYAN}    Checked {phone} ({uname}) -> Rank #{rank} | Score: {score} | Plays: {res['plays_left']}{RESET}")

    # DISPLAY RESULTS SUMMARY & DETAILS
    print(f"\n{MAGENTA}{BOLD}==================================================================================={RESET}")
    print(f"{YELLOW}{BOLD}                           AUDIT & HARVEST SUMMARY{RESET}")
    print(f"{MAGENTA}{BOLD}==================================================================================={RESET}\n")

    if confirmed_winners:
        print(f"{YELLOW}{BOLD}CONFIRMED WINNERS FOUND ({len(confirmed_winners)} Accounts):{RESET}")
        for w in confirmed_winners:
            print(f"  {BOLD}* Phone / Firebase Number :{RESET} {CYAN}{w['phone']}{RESET}")
            print(f"    {BOLD}Username              :{RESET} {w['username']}")
            print(f"    {BOLD}Leaderboard Rank      :{RESET} #{w['rank']}")
            print(f"    {BOLD}Device ID (Client ID) :{RESET} {w['device_id']}")
            print(f"    {BOLD}Firebase Panel URL    :{RESET} {w['firebase_url']}")
            
            if w['rewards']:
                for r in w['rewards']:
                    print(f"    {GREEN}{BOLD}[+] Prize Item         :{RESET} {r.get('prize_label', r.get('prize_type'))}")
                    print(f"    {GREEN}{BOLD}[+] Voucher Code       :{RESET} {BOLD}{r.get('voucher_code')}{RESET}")
                    print(f"    {GREEN}{BOLD}[+] Redemption Link    :{RESET} https://gullylabs.com/collections/thumsup-x-gully-labs")
            else:
                print(f"    {YELLOW}[+] Prize Status       : Winner Flagged on Server (Popup Triggered){RESET}")
            print("  " + "-" * 75)

    if leaderboard_under22:
        print(f"\n{GREEN}{BOLD}TOP 22 LEADERBOARD ACCOUNTS ({len(leaderboard_under22)} Accounts):{RESET}")
        for lb in leaderboard_under22:
            print(f"  {BOLD}* Rank #{lb['rank']:<2} | Phone: {CYAN}{lb['phone']}{RESET} | User: {lb['username']} | Score: {lb['score']} pts")
            print(f"    Device ID: {lb['device_id']} | Panel: {lb['firebase_url']}")

    if not confirmed_winners and not leaderboard_under22:
        print(f"{CYAN}No active accounts currently under Top 22 or holding winner prize tokens in this batch.{RESET}")

    print(f"\n{CYAN}All audit details completed & saved.{RESET}")

def main():
    print_banner()
    print(f"{BOLD}Select Operating Mode:{RESET}")
    print(f"  {CYAN}1.{RESET} {BOLD}AUTO EXTRACT & RUN{RESET}  (Scans directory for .txt session files, auto-extracts & runs audit)")
    print(f"  {CYAN}2.{RESET} {BOLD}MANUAL AUDIT{RESET}        (Runs direct audit on all existing loaded .session_*.json files)\n")

    if len(sys.argv) > 1:
        choice = sys.argv[1].strip()
    else:
        try:
            choice = input(f"{YELLOW}{BOLD}Enter choice (1 or 2): {RESET}").strip()
        except Exception:
            choice = "2"

    if choice == "1":
        print_banner()
        extract_sessions_from_text_files()
        run_auditor()
    elif choice == "2":
        print_banner()
        run_auditor()
    else:
        print(f"{RED}Invalid option selected. Exiting.{RESET}")

if __name__ == "__main__":
    main()
