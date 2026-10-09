import glob
import json
import os
import requests

BASE = "https://thunder-zone.coke2home.com"
HERE = os.path.dirname(os.path.abspath(__file__))

def audit_and_refresh_sessions():
    session_files = sorted(
        glob.glob(os.path.join(HERE, ".session_*.json")),
        key=os.path.getmtime,
        reverse=True
    )
    print(f"==================================================")
    print(f"  SESSION MANAGER & AUDITOR")
    print(f"  Found {len(session_files)} session files to evaluate")
    print(f"==================================================\n")

    active_accounts = []
    expired_accounts = []
    blocked_accounts = []

    S = requests.Session()
    S.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Origin": BASE,
        "Referer": f"{BASE}/game"
    })

    for idx, fpath in enumerate(session_files, 1):
        phone = os.path.basename(fpath).replace(".session_", "").replace(".json", "")
        
        try:
            cookies = json.load(open(fpath))
            if not cookies:
                expired_accounts.append({"phone": phone, "reason": "Empty session file"})
                continue
            
            S.cookies.clear()
            for c in cookies:
                S.cookies.set(c["name"], c["value"])
        except Exception as e:
            expired_accounts.append({"phone": phone, "reason": f"File read error: {e}"})
            continue

        try:
            # Check current session state
            r = S.get(BASE + "/api/thunder-trail/me", timeout=5)
            
            # If token expired, attempt automatic refresh using refresh_token cookie
            if r.status_code == 401:
                ref = S.post(BASE + "/api/auth/refresh", timeout=5)
                if ref.status_code == 200:
                    # Refresh successful! Save updated cookies back to disk
                    new_cookies = [{"name": c.name, "value": c.value} for c in S.cookies]
                    json.dump(new_cookies, open(fpath, "w"), indent=2)
                    r = S.get(BASE + "/api/thunder-trail/me", timeout=5)

            if r.status_code == 200 and r.json().get("success"):
                d = r.json().get("data", {})
                is_blocked = d.get("is_blocked", False)
                plays_rem = d.get("plays_remaining", 0)
                username = d.get("username", "N/A")
                best_score = d.get("best_score", 0)

                if is_blocked:
                    blocked_accounts.append({"phone": phone, "username": username})
                    print(f"[{idx:>3}/{len(session_files)}] {phone} -> BLOCKED")
                else:
                    account_info = {
                        "phone": phone,
                        "username": username,
                        "plays_remaining": plays_rem,
                        "best_score": best_score,
                        "status": "ACTIVE"
                    }
                    active_accounts.append(account_info)
                    print(f"[{idx:>3}/{len(session_files)}] {phone} -> ACTIVE ({plays_rem} plays left)")
            else:
                expired_accounts.append({"phone": phone, "reason": "Session / Refresh Token Expired"})
                print(f"[{idx:>3}/{len(session_files)}] {phone} -> EXPIRED (Requires OTP re-login)")
        except Exception as err:
            expired_accounts.append({"phone": phone, "reason": str(err)})
            print(f"[{idx:>3}/{len(session_files)}] {phone} -> Request Error")

    # Output report file
    report_file = os.path.join(HERE, "active_sessions_report.json")
    report_data = {
        "summary": {
            "total_files_scanned": len(session_files),
            "active_accounts_count": len(active_accounts),
            "expired_accounts_count": len(expired_accounts),
            "blocked_accounts_count": len(blocked_accounts)
        },
        "active_accounts": active_accounts,
        "blocked_accounts": blocked_accounts,
        "expired_accounts": expired_accounts
    }

    with open(report_file, "w") as out:
        json.dump(report_data, out, indent=2)

    print("\n==================================================")
    print(f"  AUDIT SUMMARY")
    print(f"==================================================")
    print(f"  Active & Valid Accounts : {len(active_accounts)}")
    print(f"  Expired Accounts       : {len(expired_accounts)}")
    print(f"  Blocked Accounts       : {len(blocked_accounts)}")
    print(f"  Report Saved To        : active_sessions_report.json")
    print("==================================================")

if __name__ == "__main__":
    audit_and_refresh_sessions()
