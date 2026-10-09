import os
import sys
import glob
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DIR_PATH = os.path.dirname(os.path.abspath(__file__))
BASE = "https://thunder-zone.coke2home.com"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": BASE,
    "Referer": f"{BASE}/game",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
}


def refresh_single_session(filepath: str) -> dict:
    phone = os.path.basename(filepath).replace(".session_", "").replace(".json", "")
    s = requests.Session()
    s.headers.update(HEADERS)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        for c in cookies:
            s.cookies.set(c["name"], c["value"])
    except Exception as e:
        return {"phone": phone, "status": "FAIL", "reason": f"Read error: {e}"}

    # 1. Check if current session is active
    try:
        r = s.get(f"{BASE}/api/auth/me", timeout=10)
        if r.status_code == 200 and r.json().get("success") and r.json().get("isAuthenticated"):
            user = r.json().get("user", {}).get("phone_number", phone)
            return {"phone": phone, "status": "ALREADY_ACTIVE", "reason": "Session already valid"}
    except Exception:
        pass

    # 2. Call refresh endpoint
    try:
        ref = s.post(f"{BASE}/api/auth/refresh", timeout=10)
        if ref.status_code == 200:
            # Save updated cookies back to session file
            new_cookies = [{"name": c.name, "value": c.value} for c in s.cookies]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(new_cookies, f, indent=2)

            # Verify auth status after refresh
            r_check = s.get(f"{BASE}/api/auth/me", timeout=10)
            if r_check.status_code == 200 and r_check.json().get("success"):
                return {"phone": phone, "status": "REFRESHED", "reason": "Successfully refreshed & saved"}

            return {"phone": phone, "status": "REFRESHED_SAVED", "reason": "Refresh endpoint returned 200"}
        else:
            err_msg = ref.json().get("error") if ref.headers.get("content-type", "").startswith("application/json") else ref.text[:80]
            return {"phone": phone, "status": "EXPIRED", "reason": f"HTTP {ref.status_code}: {err_msg}"}
    except Exception as e:
        return {"phone": phone, "status": "ERROR", "reason": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Refresh existing session tokens locally.")
    parser.add_argument("--workers", type=int, default=20, help="Parallel worker threads (default: 20)")
    args = parser.parse_args()

    session_files = glob.glob(os.path.join(DIR_PATH, ".session_*.json"))
    print("=" * 65, flush=True)
    print(f"🔄 SESSION TOKEN REFRESHER ({len(session_files)} local session files)", flush=True)
    print(f"⚡ Parallel Workers: {args.workers}", flush=True)
    print("=" * 65, flush=True)

    if not session_files:
        print("No .session_*.json files found to refresh.", flush=True)
        return

    already_active = 0
    refreshed_count = 0
    expired_count = 0
    error_count = 0
    completed = 0

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {executor.submit(refresh_single_session, sf): sf for sf in session_files}

        for future in as_completed(future_map):
            completed += 1
            res = future.result()
            p = res["phone"]
            st = res["status"]
            reason = res["reason"]

            if st == "ALREADY_ACTIVE":
                already_active += 1
                print(f"[{completed}/{len(session_files)}] ✅ {p} | Active (No refresh needed)", flush=True)
            elif "REFRESHED" in st:
                refreshed_count += 1
                print(f"[{completed}/{len(session_files)}] 🔄 {p} | Refreshed successfully", flush=True)
            elif st == "EXPIRED":
                expired_count += 1
                print(f"[{completed}/{len(session_files)}] ❌ {p} | Expired ({reason})", flush=True)
            else:
                error_count += 1
                print(f"[{completed}/{len(session_files)}] ⚠️ {p} | Error ({reason})", flush=True)

    print("\n" + "=" * 65, flush=True)
    print("🎉 SESSION REFRESH COMPLETED!", flush=True)
    print(f"  • Total Session Files: {len(session_files)}", flush=True)
    print(f"  • Already Active:      {already_active}", flush=True)
    print(f"  • Successfully Refreshed: {refreshed_count}", flush=True)
    print(f"  • Expired / Re-login Needed: {expired_count}", flush=True)
    print(f"  • Errors / Failures:   {error_count}", flush=True)
    print("=" * 65, flush=True)


if __name__ == "__main__":
    main()
