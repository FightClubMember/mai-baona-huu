import base64, hashlib, hmac, json, os, random, sys, time
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
    "Accept-Encoding":        "gzip, deflate, br",
    "Origin":                 BASE,
    "Referer":                f"{BASE}/game",
    "User-Agent":             "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
}

S = requests.Session()
S.headers.update(HEADERS)

def cpath(p): return os.path.join(HERE, f".session_{p}.json")

def load_session(p):
    try:
        S.cookies.clear()
        for c in json.load(open(cpath(p))): S.cookies.set(c["name"], c["value"])
        return True
    except: return False

def save_session(p):
    json.dump([{"name":c.name,"value":c.value} for c in S.cookies], open(cpath(p),"w"), indent=2)

def _wait(): time.sleep(random.uniform(0.25, 0.75))

def api(method, path, body=None):
    for i in range(2):
        r = S.request(method, BASE+path, json=body, timeout=30)
        if r.status_code==401 and i==0 and "/auth/" not in path:
            try: S.post(BASE+"/api/auth/refresh", timeout=15)
            except: pass
            _wait(); continue
        return r
    return r

def authed():
    try:
        d = api("GET","/api/auth/me").json()
        if d.get("success") and d.get("isAuthenticated"):
            return d["user"]["phone_number"]
    except: pass
    return None

def login(phone):
    r = api("POST","/api/auth/send-otp",{"phone_number":phone})
    if r.status_code != 200: sys.exit(f"OTP send failed: {r.text}")
    otp = input("Enter OTP: ").strip()
    _wait()
    r = api("POST","/api/auth/verify-otp",{"phone_number":phone,"otp":otp})
    if r.status_code != 200: sys.exit(f"OTP verify failed: {r.text}")
    v = r.json()
    ott = v.get("one_time_token") or (v.get("data") or {}).get("one_time_token")
    if ott:
        _wait()
        api("POST","/api/auth/validate-token",{"one_time_token":ott})
        _wait()
        api("POST","/api/auth/exchange-token",{"one_time_token":ott})
    save_session(phone)

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

def reaction_ms(travel):
    base = random.uniform(500, 650)
    jitter = random.gauss(0, 20)
    return max(400, base + jitter)

def chain_hash(sid, log):
    moves = ",".join(f"{e['boxId']}:{e['dir']}" for e in log)
    return hashlib.sha256(f"{sid}|{moves}".encode()).hexdigest()

def run():
    min_duration = 105.0
    max_duration = 112.0
    
    print(f"\nAuto-running. Target score: 2900-3600 | Stop at {min_duration}s or HP=0.\n")

    time.sleep(random.uniform(1.2, 3.5))
    r = api("POST","/api/thunder-trail/sessions",{})
    if r.status_code not in (200,201): sys.exit(f"Session open failed: {r.text}")
    d = r.json()["data"]
    sid, token = d["session_id"], d["session_token"]
    seed = d.get("seed", 0)
    print(f"Session: {sid[:12]}... | Seed: {seed}")

    floats = decrypt_drip(sid, d.get("drip_enc",""))
    print(f"Floats decrypted: {len(floats)} ({len(floats)//2} boxes)")

    time.sleep(random.uniform(2.5, 4.5))

    hp = 3
    score, nxt, bid = 0, 0.0, 1
    combo, max_combo = 0, 0
    hits, last_types, log = {}, [], []
    cursor, committed = 0, 0
    heart_gate = {"boxes":0,"traps":0,"others":0,"hp_last":3}
    pending_hg = None

    t0 = time.time()
    last_hb = t0
    hb_n = 0

    while True:
        elapsed = time.time() - t0
        if hp <= 0:
            print(f"\nHP reached 0. Stopping.")
            break
        if elapsed >= max_duration:
            break

        gms = elapsed * 1000.0

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
                print(f"\nRefill: {len(nf)} floats at box #{fb2}")

        if gms < nxt:
            time.sleep(min(0.04, (nxt-gms)/1000.0))
            continue

        spawn_ms = nxt
        sp_ev, travel = get_tier(spawn_ms)
        nxt += sp_ev

        if cursor >= len(floats):
            print("\nOut of floats, breaking to submit safely.")
            break
        fv_t = floats[cursor]; cursor += 1
        if cursor >= len(floats):
            print("\nOut of floats, breaking to submit safely.")
            break
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

        # Realistic human swipe reaction time with tier scaling and natural variance
        swipe_at = spawn_ms + reaction_ms(travel) + random.uniform(-25, 35)

        # Simulate natural human mistakes (take damage / break combo)
        # Drops HP when HP > 1 so we can recover life via hearts later!
        is_miss = False
        if hp > 1 and random.random() < 0.035:  # ~3.5% human miss chance
            is_miss = True

        if is_miss:
            # Wrong swipe direction to simulate accidental miss
            swipe_dir = OPP[barrow] if btype != "trap" else barrow
            hp -= 1
            combo = 0
            # Miss doesn't gain points
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
            if hp < 3: 
                hp += 1 # Recover life!
            combo += 1; max_combo = max(max_combo, combo)
            hits["heart"] = hits.get("heart",0) + 1

        now = time.time()
        wait = t0 + swipe_at/1000.0 - now
        if wait > 0: time.sleep(wait)

        log.append({"boxId":bid,"dir":swipe_dir,"atMs":round(swipe_at,1),
                    "spawnAtMs":round(spawn_ms,1)})
        bid += 1

        now = time.time()
        hb_interval = random.uniform(4.2, 6.2)
        if now - last_hb >= hb_interval:
            delta = [{"boxId":e["boxId"],"dir":e["dir"],"atMs":e["atMs"],"spawnAtMs":e["spawnAtMs"]}
                     for e in log[committed:]]
            hb_pay = {"session_token":token,"boxes_seen":len(log),"score_so_far":score,
                      "paused":False,"at_ms":round(swipe_at,1),"boxes_committed":len(log),
                      "chain_hash":chain_hash(sid,log),"input_log_delta":delta}
            hr = api("POST",f"/api/thunder-trail/sessions/{sid}/heartbeat",hb_pay)
            if hr.status_code == 200:
                hb_n += 1; committed = len(log); last_hb = now
                hd = hr.json()
                if hd.get("drip_enc"):
                    nf2 = decrypt_drip(sid,hd["drip_enc"])
                    fb3 = hd.get("drip_from_box",0)
                    ti2 = 2*fb3
                    if ti2>len(floats): floats.extend([0.5]*(ti2-len(floats)))
                    floats[ti2:ti2+len(nf2)] = nf2

        sys.stdout.write(f"\r Score: {score} | HP: {hp}/3 | Box: #{bid-1} | Combo: {combo} | HB: #{hb_n} ")
        sys.stdout.flush()

    dur = (time.time() - t0) * 1000.0
    if log:
        dur = log[-1]["atMs"] + random.uniform(280, 480)

    print(f"\n\nScore   : {score}")
    print(f"Moves   : {len(log)}")
    print(f"Combo   : {max_combo}")
    print(f"Dur     : {dur/1000:.1f}s")

    bc = {}
    for k,v in hits.items():
        mk = CMAP.get(k,k); bc[mk] = bc.get(mk,0) + v

    delta_fin = [{"boxId":e["boxId"],"dir":e["dir"],"atMs":e["atMs"],"spawnAtMs":e["spawnAtMs"]}
                 for e in log[committed:]]
    api("POST",f"/api/thunder-trail/sessions/{sid}/heartbeat",{
        "session_token":token,"boxes_seen":len(log),"score_so_far":score,
        "paused":False,"at_ms":round(dur,1),"boxes_committed":len(log),
        "chain_hash":chain_hash(sid,log),"input_log_delta":delta_fin
    })

    _wait()
    jr_pay = {"session_token":token,"seed":seed,"input_log":log,"final_score":score,
              "duration_ms":round(dur,1),"max_combo":max_combo,"hit_counts":bc,
              "max_tier_reached":get_tier_idx(dur)+1}
    jr = api("POST",f"/api/thunder-trail/sessions/{sid}/journey",jr_pay)
    print(f"\n[Journey] {jr.status_code} | {jr.text}")
    
    final_submit_score = score
    try:
        jd = jr.json().get("data",{})
        if "recomputed_score" in jd and jd["recomputed_score"] is not None:
            final_submit_score = jd["recomputed_score"]
            if final_submit_score != score:
                print(f"[Sync] Using server recomputed score: {final_submit_score} (Local was {score})")
    except Exception as e:
        print(f"[Sync Error] {e}")

    _wait()
    sc_pay = {"session_token":token,"final_score":final_submit_score,"duration_ms":round(dur,1),
              "max_combo":max_combo,"box_counts":bc,"seed":seed,"input_log":log}
    sr = api("POST",f"/api/thunder-trail/sessions/{sid}/score",sc_pay)
    print(f"[Score]   {sr.status_code} | {sr.text}")

    time.sleep(2.0)
    br = api("GET","/api/thunder-trail/sub-leaderboard")
    if br.status_code == 200:
        bd = br.json().get("data",{})
        print("\n" + "="*50)
        print("  LEADERBOARD - TOP 15")
        print("="*50)
        for e in (bd.get("entries") or [])[:15]:
            you = " <-- YOU" if e.get("is_me") else ""
            print(f"  #{e['rank']:>2}  {e['username']:<16}{e['score']:>6}{you}")
        print("-"*50)
        print(f"  Your Rank  : {bd.get('me_rank')}")
        print(f"  Your Score : {bd.get('me_score')}")
        print("="*50)

def main():
    print("="*44)
    print("  Thunder Trail Bot")
    print("="*44)

    raw = input("\nMobile number (10 digits): ").strip()
    phone = "".join(c for c in raw if c.isdigit())[-10:]
    if len(phone) != 10: sys.exit("Need 10 digits.")

    if load_session(phone) and authed() == phone:
        print("Session active — no OTP needed")
    else:
        S.cookies.clear()
        login(phone)

    me = api("GET","/api/thunder-trail/me").json().get("data",{})
    print(f"\n  Username   : {me.get('username')}")
    print(f"  Best Score : {me.get('best_score')}")
    print(f"  Plays Left : {me.get('plays_remaining')} / 5")
    print(f"  Resets At  : {me.get('resets_at')}")

    if me.get("plays_remaining", 0) == 0:
        print("\nNo plays left today. Resets at midnight IST.")
        return

    run()

if __name__ == "__main__":
    main()
