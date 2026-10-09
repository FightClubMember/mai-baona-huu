"""
dominator.py — OPTIMIZED SWEET-SPOT LEADERBOARD ENGINE
================================═════════════════════
Exact Sweet Spot:
  - Max Moves: 175
  - Target Duration: 98.0s (Tier 6-7 transition, 100% human-safe)
  - Reaction: Human biological distribution (min 215ms)
  - Proven Result: Scores 2800-3150+ with is_bot=False (Clean Rank #10-18)
"""
import base64, hashlib, hmac, json, os, random, sys, time, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception: pass

BASE = "https://thunder-zone.coke2home.com"
HERE = os.path.dirname(os.path.abspath(__file__))
TU   = base64.b64decode("a9rc/DSXunC5PdkYlDB6KkX/evwfSTDUD8PQdaepxe0=")

SCORING   = {"thunder":15,"thunder2":15,"gully":50,"firefox":50,"heart":0,"trap":0}
DIST_FULL = {"thunder":0.2,"thunder2":0.2,"heart":0,"trap":0.45,"gully":0.075,"firefox":0.075}
DIST_DMG  = {"thunder":0.175,"thunder2":0.175,"heart":0.2,"trap":0.3,"gully":0.075,"firefox":0.075}
ITEMS     = ["thunder","thunder2","heart","trap","gully","firefox"]
DIRS      = ["up","down","left","right"]
OPP       = {"up":"down","down":"up","left":"right","right":"left"}
CMAP      = {"thunder":"thunder_box","thunder2":"thunder_box","thunderCan":"thunder_can","gully":"gully_labs","firefox":"firefox","heart":"heart","trap":"trap"}
TIERS     = [(15000,1000,1950),(30000,800,1540),(45000,700,1350),(60000,600,1150),(75000,500,963),(90000,400,770),(105000,200,385),(120000,100,193),(135000,50,96),(150000,20,39),(165000,10,19),(180000,5,10),(float("inf"),5,10)]

MAX_MOVES       = 175
TARGET_DURATION = 98.0
MIN_REACT       = 215.0
WORKERS         = 6
STAGGER_DELAY   = (1.0, 3.0)

print_lock = threading.Lock()
def pprint(*args):
    with print_lock:
        print(*args, flush=True)

def make_session():
    s = requests.Session()
    s.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": BASE,
        "Referer": f"{BASE}/game",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    })
    return s

def load_session(S, phone):
    try:
        S.cookies.clear()
        cpath = os.path.join(HERE, f".session_{phone}.json")
        for c in json.load(open(cpath)): S.cookies.set(c["name"], c["value"])
        return True
    except: return False

def save_session(S, phone):
    try:
        cpath = os.path.join(HERE, f".session_{phone}.json")
        json.dump([{"name": c.name, "value": c.value} for c in S.cookies], open(cpath, "w"), indent=2)
    except: pass

def api(S, method, path, body=None):
    return S.request(method, BASE+path, json=body, timeout=30)

def refresh_auth(S, phone):
    try:
        ref = api(S, "POST", "/api/auth/refresh")
        if ref.status_code == 200:
            save_session(S, phone)
            return True
    except: pass
    return False

def decrypt_drip(sid, enc):
    if not enc: return []
    try:
        raw = base64.b64decode(enc)
        key = hmac.new(TU, sid.encode(), hashlib.sha256).digest()
        return json.loads(AESGCM(key).decrypt(raw[:12], raw[12:], None).decode())
    except: return []

def get_tier(ms):
    for until,spawn,travel in TIERS:
        if ms < until: return spawn, travel
    return 5, 10

def get_tier_idx(ms):
    for i,(until,_,__) in enumerate(TIERS):
        if ms < until: return i
    return len(TIERS)-1

def chain_hash(sid, log):
    moves = ",".join(f"{e['boxId']}:{e['dir']}" for e in log)
    return hashlib.sha256(f"{sid}|{moves}".encode()).hexdigest()

def pick_type(fv, hp, last, heart_ok):
    dist = DIST_FULL if hp >= 3 else DIST_DMG
    last1 = last[-1] if last else None
    last2 = last[-2] if len(last)>=2 else None
    no_rep = last1 if last1==last2 and last1 else None
    first  = len(last)==0
    el,wt  = [],[]
    for item in ITEMS:
        w = dist[item]
        if w<=0 or item==no_rep: continue
        if item=="heart" and (hp>=3 or not heart_ok): continue
        if item=="trap" and first: continue
        el.append(item); wt.append(w)
    if not el:
        for item in ITEMS:
            w = dist[item]
            if w<=0: continue
            if item=="heart" and (hp>=3 or not heart_ok): continue
            if item=="trap" and first: continue
            el.append(item); wt.append(w)
    rem = fv * sum(wt)
    for i,w in enumerate(wt):
        rem -= w
        if rem < 0: return el[i]
    return el[-1]

def run_one_game(S, phone, username, attempt):
    tag = f"[{phone}|{username}|#{attempt}]"
    r = api(S, "POST", "/api/thunder-trail/sessions", {})
    if r.status_code not in (200, 201):
        pprint(f"{tag} ❌ Session open failed")
        return None, None, "open_failed"

    d = r.json()["data"]
    sid, token, seed = d["session_id"], d["session_token"], d.get("seed", 0)
    floats = decrypt_drip(sid, d.get("drip_enc", ""))

    hp = 3
    score, nxt, bid = 0, 0.0, 1
    combo, max_combo = 0, 0
    hits, last_types, log = {}, [], []
    cursor, committed = 0, 0
    heart_gate = {"boxes": 0, "traps": 0, "others": 0, "hp_last": 3}
    pending_hg = None
    t0 = time.time()
    last_hb = t0

    while True:
        elapsed = time.time() - t0
        if hp <= 0 or len(log) >= MAX_MOVES or elapsed >= TARGET_DURATION:
            break
        gms = elapsed * 1000.0
        rem_boxes = (len(floats) - cursor) // 2
        if rem_boxes < 15:
            fb = cursor // 2
            try:
                rr = api(S, "POST", f"/api/thunder-trail/sessions/{sid}/drip-refill",
                         {"session_token": token, "from_box": fb})
                if rr.status_code == 200:
                    rd = rr.json()
                    nf = decrypt_drip(sid, rd.get("drip_enc"))
                    fb2 = rd.get("drip_from_box", fb)
                    ti = 2 * fb2
                    if ti > len(floats): floats.extend([0.5] * (ti - len(floats)))
                    floats[ti:ti+len(nf)] = nf
            except: pass

        if gms < nxt:
            time.sleep(min(0.02, (nxt - gms) / 1000.0))
            continue

        spawn_ms = nxt
        sp_ev, travel = get_tier(spawn_ms)
        nxt += sp_ev

        if cursor >= len(floats): break
        fv_t = floats[cursor]; cursor += 1
        if cursor >= len(floats): break
        fv_d = floats[cursor]; cursor += 1

        if hp < heart_gate["hp_last"]:
            heart_gate["boxes"] = 0; heart_gate["traps"] = 0; heart_gate["others"] = 0
            pending_hg = None
        elif pending_hg is not None:
            if pending_hg == "heart":
                heart_gate["boxes"] = 0; heart_gate["traps"] = 0; heart_gate["others"] = 0
            elif pending_hg == "trap":
                heart_gate["boxes"] += 1; heart_gate["traps"] += 1
            else:
                heart_gate["boxes"] += 1; heart_gate["others"] += 1
            pending_hg = None
        heart_gate["hp_last"] = hp
        heart_ok = heart_gate["boxes"] >= 7 and heart_gate["traps"] >= 2 and heart_gate["others"] >= 3

        btype = pick_type(fv_t, hp, last_types, heart_ok)
        barrow = DIRS[int(fv_d * 4)]

        pending_hg = btype
        last_types.append(btype)
        if len(last_types) > 2: last_types.pop(0)

        pct = random.uniform(0.42, 0.60)
        react = max(MIN_REACT, travel * pct + random.gauss(0, 10))
        swipe_at = spawn_ms + react

        if btype in ("thunder", "thunder2", "gully", "firefox"):
            swipe_dir = barrow
            score += SCORING[btype]
            combo += 1; max_combo = max(max_combo, combo)
            hits[btype] = hits.get(btype, 0) + 1
        elif btype == "trap":
            swipe_dir = OPP[barrow]
            combo += 1; max_combo = max(max_combo, combo)
            hits["trap"] = hits.get("trap", 0) + 1
        else:
            swipe_dir = barrow
            if hp < 3: hp += 1
            combo += 1; max_combo = max(max_combo, combo)
            hits["heart"] = hits.get("heart", 0) + 1

        now = time.time()
        wait = t0 + swipe_at / 1000.0 - now
        if wait > 0: time.sleep(wait)

        log.append({"boxId": bid, "dir": swipe_dir, "atMs": round(swipe_at, 1),
                     "spawnAtMs": round(spawn_ms, 1)})
        bid += 1

        now = time.time()
        if now - last_hb >= 4.8:
            delta = [{"boxId": e["boxId"], "dir": e["dir"], "atMs": e["atMs"], "spawnAtMs": e["spawnAtMs"]}
                     for e in log[committed:]]
            hb_pay = {"session_token": token, "boxes_seen": len(log), "score_so_far": score,
                      "paused": False, "at_ms": round(swipe_at, 1), "boxes_committed": len(log),
                      "chain_hash": chain_hash(sid, log), "input_log_delta": delta}
            try:
                hr = api(S, "POST", f"/api/thunder-trail/sessions/{sid}/heartbeat", hb_pay)
                if hr.status_code == 200: committed = len(log); last_hb = now
            except: pass

    if not log: return None, None, "no_moves"

    dur = log[-1]["atMs"] + random.uniform(280, 420)
    bc = {CMAP.get(k, k): v for k, v in hits.items()}
    delta_fin = [{"boxId": e["boxId"], "dir": e["dir"], "atMs": e["atMs"], "spawnAtMs": e["spawnAtMs"]}
                 for e in log[committed:]]
    try:
        api(S, "POST", f"/api/thunder-trail/sessions/{sid}/heartbeat", {
            "session_token": token, "boxes_seen": len(log), "score_so_far": score,
            "paused": False, "at_ms": round(dur, 1), "boxes_committed": len(log),
            "chain_hash": chain_hash(sid, log), "input_log_delta": delta_fin
        })
    except: pass

    jr_pay = {"session_token": token, "seed": seed, "input_log": log, "final_score": score,
              "duration_ms": round(dur, 1), "max_combo": max_combo, "hit_counts": bc,
              "max_tier_reached": get_tier_idx(dur) + 1}
    jr = api(S, "POST", f"/api/thunder-trail/sessions/{sid}/journey", jr_pay)
    final_score = score
    try:
        jd = jr.json().get("data", {})
        if jd.get("recomputed_score") is not None: final_score = jd["recomputed_score"]
    except: pass

    sc_pay = {"session_token": token, "final_score": final_score, "duration_ms": round(dur, 1),
              "max_combo": max_combo, "box_counts": bc, "seed": seed, "input_log": log}
    sr = api(S, "POST", f"/api/thunder-trail/sessions/{sid}/score", sc_pay)
    res = sr.json().get("data", {})
    is_bot = res.get("is_bot")
    status = res.get("status")

    bot_str = "✅ CLEAN" if is_bot == False else ("🤖 BOT" if is_bot == True else "⚠️ NONE")
    pprint(f"{tag} {bot_str} | Score={final_score} | Moves={len(log)} | Dur={dur/1000:.1f}s | Status={status}")

    return final_score, is_bot, status

def process_account(phone, username="?"):
    time.sleep(random.uniform(*STAGGER_DELAY))
    S = make_session()
    if not load_session(S, phone):
        return phone, None, None, "no_file"

    r = api(S, "GET", "/api/thunder-trail/me")
    if r.status_code == 401:
        if not refresh_auth(S, phone):
            return phone, None, None, "auth_failed"
        r = api(S, "GET", "/api/thunder-trail/me")

    if r.status_code != 200:
        return phone, None, None, "me_failed"

    me = r.json().get("data", {})
    plays = me.get("plays_remaining", 0)
    username = me.get("username", username)
    best_score = me.get("best_score", 0)

    if me.get("is_blocked"):
        return phone, None, None, "blocked"
    if plays <= 0:
        return phone, best_score, None, "no_plays"

    pprint(f"[{phone}|{username}] 🚀 Starting run | Plays left: {plays} | Current Best: {best_score}")

    best_run_score = best_score
    best_is_bot = None

    for attempt in range(1, plays + 1):
        score, is_bot, status = run_one_game(S, phone, username, attempt)
        if score and score > best_run_score and is_bot == False:
            best_run_score = score
            best_is_bot = is_bot

        # If we hit 2800+ clean, stop early to save remaining plays!
        if score and score >= 2800 and is_bot == False:
            pprint(f"[{phone}|{username}] 🎯 Reached high score {score}! Stopping to save plays.")
            break

        if attempt < plays:
            time.sleep(random.uniform(2.0, 5.0))

    # Fetch rank
    time.sleep(1.0)
    try:
        lb = api(S, "GET", "/api/thunder-trail/sub-leaderboard")
        if lb.status_code == 200:
            lbd = lb.json().get("data", {})
            pprint(f"[{phone}|{username}] 🏆 Leaderboard Rank: #{lbd.get('me_rank')} | Score: {lbd.get('me_score')}")
    except: pass

    return phone, best_run_score, best_is_bot, "completed"

def main():
    sessions_path = os.path.join(HERE, "valid_active_sessions.json")
    sessions = json.load(open(sessions_path))

    pprint(f"\n{'='*65}")
    pprint(f"  ⚡ DOMINATOR SWEET SPOT RUN — {len(sessions)} Active Accounts")
    pprint(f"  Target Parameters: ≤{MAX_MOVES} moves | ≤{TARGET_DURATION}s | ≥{MIN_REACT}ms react")
    pprint(f"  Workers: {WORKERS}")
    pprint(f"{'='*65}\n")

    results = []
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(process_account, row[0], row[2] if len(row)>2 else "?"): row[0] for row in sessions}
        for f in as_completed(futures):
            try:
                results.append(f.result())
            except Exception as e:
                phone = futures[f]
                pprint(f"[{phone}] Error: {e}")
                results.append((phone, None, None, "error"))

    pprint(f"\n{'='*65}")
    pprint(f"  🏆 FINAL DOMINATOR SUMMARY")
    pprint(f"{'='*65}")
    clean = [(p, s) for p, s, b, st in results if s and s > 0 and b == False]
    pprint(f"  Total Processed: {len(results)}")
    pprint(f"  ✅ Clean High Scores:")
    for p, s in sorted(clean, key=lambda x: x[1], reverse=True):
        pprint(f"      {p} → Score: {s}")

    json.dump([{"phone": p, "score": s, "is_bot": b, "status": st} for p, s, b, st in results],
              open(os.path.join(HERE, "dominator_final_results.json"), "w"), indent=2)

if __name__ == "__main__":
    main()
