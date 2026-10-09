import base64, glob, hashlib, hmac, json, os, random, sys, time
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE = "https://thunder-zone.coke2home.com"
HERE = os.path.dirname(os.path.abspath(__file__))
TU   = base64.b64decode("a9rc/DSXunC5PdkYlDB6KkX/evwfSTDUD8PQdaepxe0=")

SCORING     = {"thunder":15,"thunder2":15,"gully":50,"firefox":50,"heart":0,"trap":0}
DIST_FULL   = {"thunder":0.2,"thunder2":0.2,"heart":0,"trap":0.45,"gully":0.075,"firefox":0.075}
DIST_DMG    = {"thunder":0.175,"thunder2":0.175,"heart":0.2,"trap":0.3,"gully":0.075,"firefox":0.075}
ITEMS       = ["thunder","thunder2","heart","trap","gully","firefox"]
DIRS        = ["up","down","left","right"]
OPP         = {"up":"down","down":"up","left":"right","right":"left"}
CMAP        = {"thunder":"thunder_box","thunder2":"thunder_box","thunderCan":"thunder_can",
               "gully":"gully_labs","firefox":"firefox","heart":"heart","trap":"trap"}

TIERS       = [
    (15000,1000,1950),(30000,800,1540),(45000,700,1350),(60000,600,1150),
    (75000,500,963),(90000,400,770),(105000,200,385),(120000,100,193),
    (135000,50,96),(150000,20,39),(165000,10,19),(180000,5,10),(float("inf"),5,10)
]

HEADERS = {
    "Content-Type":           "application/json",
    "Accept":                 "application/json, text/plain, */*",
    "Accept-Language":        "en-US,en;q=0.9",
    "Origin":                 BASE,
    "Referer":                f"{BASE}/game",
    "User-Agent":             "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
}

S = requests.Session()
S.headers.update(HEADERS)

def load_session(p):
    try:
        S.cookies.clear()
        for c in json.load(open(os.path.join(HERE, f".session_{p}.json"))): 
            S.cookies.set(c["name"], c["value"])
        return True
    except: return False

def api(method, path, body=None):
    return S.request(method, BASE+path, json=body, timeout=30)

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

def run_experiment(phone, profile):
    """
    profile keys:
    - miss_rate: float (e.g. 0.06)
    - max_moves: int (e.g. 190)
    - target_duration: float (e.g. 105.0)
    - pause_sec: float (simulate in-game pause)
    """
    if not load_session(phone):
        return None

    r = api("POST","/api/thunder-trail/sessions",{})
    if r.status_code not in (200,201):
        return None

    d = r.json()["data"]
    sid, token, seed = d["session_id"], d["session_token"], d.get("seed", 0)
    floats = decrypt_drip(sid, d.get("drip_enc",""))

    hp = 3
    score, nxt, bid = 0, 0.0, 1
    combo, max_combo = 0, 0
    hits, last_types, log = {}, [], []
    cursor, committed = 0, 0
    heart_gate = {"boxes":0,"traps":0,"others":0,"hp_last":3}
    pending_hg = None

    t0 = time.time()
    last_hb = t0
    last_dir = None
    paused_time_total = 0.0

    target_duration = profile.get("target_duration", 105.0)
    max_moves = profile.get("max_moves", 190)
    miss_rate = profile.get("miss_rate", 0.05)
    do_pause = profile.get("do_pause", False)

    pause_triggered = False

    while True:
        elapsed = (time.time() - t0) - paused_time_total
        if hp <= 0 or len(log) >= max_moves or elapsed >= target_duration:
            break

        gms = elapsed * 1000.0

        # Simulate human mid-game pause if enabled
        if do_pause and not pause_triggered and elapsed > 45.0:
            pause_triggered = True
            p_dur = random.uniform(2.5, 4.0)
            time.sleep(p_dur)
            paused_time_total += p_dur
            continue

        rem_boxes = (len(floats) - cursor) // 2
        if rem_boxes < 15:
            fb = cursor // 2
            rr = api("POST", f"/api/thunder-trail/sessions/{sid}/drip-refill",
                          {"session_token":token,"from_box":fb})
            if rr.status_code == 200:
                rd = rr.json()
                nf = decrypt_drip(sid, rd.get("drip_enc"))
                fb2 = rd.get("drip_from_box", fb)
                ti = 2 * fb2
                if ti > len(floats): floats.extend([0.5]*(ti-len(floats)))
                floats[ti:ti+len(nf)] = nf

        if gms < nxt:
            time.sleep(min(0.02, (nxt-gms)/1000.0))
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
        heart_ok = heart_gate["boxes"]>=7 and heart_gate["traps"]>=2 and heart_gate["others"]>=3

        btype  = pick_type(fv_t, hp, last_types, heart_ok)
        barrow = DIRS[int(fv_d * 4)]

        pending_hg = btype
        last_types.append(btype)
        if len(last_types) > 2: last_types.pop(0)

        # Human reaction dynamics
        pct = random.uniform(0.40, 0.65)
        base_react = travel * pct
        dir_switch = random.uniform(40, 100) if (last_dir and barrow != last_dir) or btype == "trap" else 0
        
        react = max(210.0, base_react + dir_switch + random.gauss(0, 15))
        swipe_at = spawn_ms + react
        last_dir = barrow

        # Human mistake calculation
        is_miss = False
        if hp > 1 and random.random() < miss_rate:
            is_miss = True

        if is_miss:
            swipe_dir = OPP[barrow] if btype != "trap" else barrow
            hp -= 1
            combo = 0
        elif btype in ("thunder","thunder2","gully","firefox"):
            swipe_dir = barrow
            score += SCORING[btype]
            combo += 1; max_combo = max(max_combo, combo)
            hits[btype] = hits.get(btype,0) + 1
        elif btype == "trap":
            swipe_dir = OPP[barrow]
            combo += 1; max_combo = max(max_combo, combo)
            hits["trap"] = hits.get("trap",0) + 1
        else: # heart item
            swipe_dir = barrow
            if hp < 3: hp += 1
            combo += 1; max_combo = max(max_combo, combo)
            hits["heart"] = hits.get("heart",0) + 1

        now = time.time()
        wait = t0 + paused_time_total + swipe_at/1000.0 - now
        if wait > 0: time.sleep(wait)

        log.append({"boxId":bid,"dir":swipe_dir,"atMs":round(swipe_at,1),
                    "spawnAtMs":round(spawn_ms,1)})
        bid += 1

        now = time.time()
        if now - last_hb >= 4.8:
            delta = [{"boxId":e["boxId"],"dir":e["dir"],"atMs":e["atMs"],"spawnAtMs":e["spawnAtMs"]}
                     for e in log[committed:]]
            hb_pay = {"session_token":token,"boxes_seen":len(log),"score_so_far":score,
                      "paused":do_pause and pause_triggered, "at_ms":round(swipe_at,1),"boxes_committed":len(log),
                      "chain_hash":chain_hash(sid,log),"input_log_delta":delta}
            hr = api("POST",f"/api/thunder-trail/sessions/{sid}/heartbeat",hb_pay)
            if hr.status_code == 200:
                committed = len(log); last_hb = now

    dur = log[-1]["atMs"] + random.uniform(280, 450) if log else 1000.0
    bc = {CMAP.get(k,k): v for k,v in hits.items()}

    delta_fin = [{"boxId":e["boxId"],"dir":e["dir"],"atMs":e["atMs"],"spawnAtMs":e["spawnAtMs"]}
                 for e in log[committed:]]
    api("POST",f"/api/thunder-trail/sessions/{sid}/heartbeat",{
        "session_token":token,"boxes_seen":len(log),"score_so_far":score,
        "paused":False,"at_ms":round(dur,1),"boxes_committed":len(log),
        "chain_hash":chain_hash(sid,log),"input_log_delta":delta_fin
    })

    jr_pay = {"session_token":token,"seed":seed,"input_log":log,"final_score":score,
              "duration_ms":round(dur,1),"max_combo":max_combo,"hit_counts":bc,
              "max_tier_reached":get_tier_idx(dur)+1}
    jr = api("POST",f"/api/thunder-trail/sessions/{sid}/journey",jr_pay)

    final_score = score
    try:
        jd = jr.json().get("data",{})
        if jd.get("recomputed_score") is not None:
            final_score = jd["recomputed_score"]
    except: pass

    sc_pay = {"session_token":token,"final_score":final_score,"duration_ms":round(dur,1),
              "max_combo":max_combo,"box_counts":bc,"seed":seed,"input_log":log}
    sr = api("POST",f"/api/thunder-trail/sessions/{sid}/score",sc_pay)

    res = sr.json().get("data",{})
    is_bot = res.get("is_bot")
    status = res.get("status")

    res_summary = {
        "phone": phone,
        "final_score": final_score,
        "moves": len(log),
        "max_combo": max_combo,
        "duration_s": round(dur/1000, 1),
        "is_bot": is_bot,
        "status": status,
        "profile": profile
    }
    print(f"[{phone}] Score: {final_score} | Moves: {len(log)} | Combo: {max_combo} | Dur: {round(dur/1000,1)}s | is_bot: {is_bot}")
    return res_summary

def batch_runner():
    valid = json.load(open(os.path.join(HERE, "valid_active_sessions.json")))
    print(f"Loaded {len(valid)} sessions from valid_active_sessions.json")

    # Profiles to test to crack >2505 with is_bot: False
    profiles = [
        {"name": "Human Imperfect Combo 1", "max_moves": 185, "target_duration": 104.0, "miss_rate": 0.07, "do_pause": False},
        {"name": "Human Imperfect Combo 2", "max_moves": 190, "target_duration": 108.0, "miss_rate": 0.09, "do_pause": False},
        {"name": "Human Mid-Game Pause 1", "max_moves": 185, "target_duration": 105.0, "miss_rate": 0.05, "do_pause": True},
        {"name": "Human Imperfect Combo High Yield", "max_moves": 195, "target_duration": 110.0, "miss_rate": 0.08, "do_pause": False},
    ]

    results = []
    successes = []

    p_idx = 0
    for phone, plays, user in valid:
        if plays <= 0: continue
        prof = profiles[p_idx % len(profiles)]
        p_idx += 1
        
        res = run_experiment(phone, prof)
        if res:
            results.append(res)
            if res["final_score"] >= 2505 and res["is_bot"] == False:
                print(f"\n🎉 SUCCESS FOUND ON {phone}! SCORE: {res['final_score']} | IS_BOT: False")
                successes.append(res)
                # Keep hunting to get more winning sessions!

    with open(os.path.join(HERE, "experiment_results.json"), "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n==================================================")
    print(f"  BATCH COMPLETED: Found {len(successes)} Winning Sessions (>2505 score, is_bot: False)")
    print(f"==================================================")
    for s in successes:
        print(f"  -> Phone: {s['phone']} | Score: {s['final_score']} | Moves: {s['moves']} | Profile: {s['profile']['name']}")

if __name__ == "__main__":
    batch_runner()
