import json, os, requests

BASE = "https://thunder-zone.coke2home.com"
HERE = os.path.dirname(os.path.abspath(__file__))

def check_rewards(phone):
    session_file = os.path.join(HERE, f".session_{phone}.json")
    if not os.path.exists(session_file):
        print(f"No saved session file found for phone {phone}")
        return

    S = requests.Session()
    S.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Origin": BASE,
        "Referer": f"{BASE}/game"
    })

    cookies = json.load(open(session_file))
    for c in cookies:
        S.cookies.set(c["name"], c["value"])

    print(f"\n==========================================")
    print(f" Checking Account Session: {phone}")
    print(f"==========================================")

    # Refresh auth check
    me_resp = S.get(BASE + "/api/auth/me")
    if me_resp.status_code == 401:
        ref_resp = S.post(BASE + "/api/auth/refresh")
        if ref_resp.status_code == 200:
            # Update saved session file with refreshed cookies
            cookie_list = [{"name": c.name, "value": c.value} for c in S.cookies]
            json.dump(cookie_list, open(session_file, "w"), indent=2)
        me_resp = S.get(BASE + "/api/auth/me")

    if me_resp.status_code != 200 or not me_resp.json().get("isAuthenticated"):
        print("[Auth Error] Session has expired or is invalid. Please log in again to save a fresh session.")
        return

    user_data = me_resp.json().get("user", {})
    print(f"  Phone Number : {user_data.get('phone_number')}")
    print(f"  Full Name    : {user_data.get('full_name') or 'N/A'}")

    # Check Thunder Trail Stats
    tt_me = S.get(BASE + "/api/thunder-trail/me").json().get("data", {})
    print(f"\n--- Thunder Trail Stats ---")
    print(f"  Username     : {tt_me.get('username')}")
    print(f"  Best Score   : {tt_me.get('best_score')}")
    print(f"  Plays Left   : {tt_me.get('plays_remaining')}")

    # Check My Rewards
    rewards_resp = S.get(BASE + "/api/thunder-trail/my-rewards")
    print(f"\n--- Rewards Status ---")
    if rewards_resp.status_code == 200:
        rw_data = rewards_resp.json()
        print(json.dumps(rw_data, indent=2))
    else:
        print(f"  Status {rewards_resp.status_code}: {rewards_resp.text}")

    # Check Winners Status
    winner_resp = S.get(BASE + "/api/winners/status")
    if winner_resp.status_code == 200:
        print(f"\n--- Winner Status ---")
        print(json.dumps(winner_resp.json(), indent=2))

if __name__ == "__main__":
    import sys
    phone_input = sys.argv[1] if len(sys.argv) > 1 else "6375555137"
    check_rewards(phone_input)
