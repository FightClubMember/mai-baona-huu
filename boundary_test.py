"""
boundary_test.py - Find the EXACT highest move count and duration
that still returns is_bot: False.

Tests:
  - Move counts: 166, 167, 168, 169, 170, 171, 172
  - Duration: held constant at 93.5s while testing moves
  - Duration: tested at 95s, 96s, 97s, 98s with 165 moves

Uses 1 account per test, reports is_bot result clearly.
"""
import base64, hashlib, hmac, json, os, random, sys, time
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
CMAP      = {"thunder":"thunder_box","thunder2":"thunder_box","thunderCan":"thunder_can",
             "gully":"gully_labs","firefox":"firefox","heart":"heart","trap":"trap"}
TIERS     = [
    (15000,1000,1950),(30000,800,1540),(45000,700,1350),(60000,600,1150),
    (75000,500,963),(90000,400,770),(105000,200,385),(120000,100,193),
    (135000,50,96),(150000,20,39),(165000,10,19),(180000,5,10),(float("inf"),5,10)
]

def make_s():
    s = requests.Session()
    s.headers.update({
        "Content-Type":"application/json","Accept":"application/json, text/plain, */*",
        "Origin":BASE,"Referer":f"{BASE}/game",
        "User-Agent":"Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36",
    })
    return s

def load_session(S, phone):
    try:
        S.cookies.clear()
        for c in json.load(open(os.path.join(HERE, f".session_{phone}.json"))): S.cookies.set(c["name"],c["value"])
        return True
    except: return False

def api(S, m, p, b=None): return S.request(m, BASE+p, json=b, timeout=30)

def decrypt_drip(sid, enc):
    if not enc: return []
    try:
        raw = base64.b64decode(enc)
        key = hmac.new(TU, sid.encode(), hashlib.sha256).digest()
        return json.loads(AESGCM(key).decrypt(raw[:12],raw[12:],None).decode())
    except: return []

def get_tier(ms):
    for until,spawn,travel in TIERS:
        if ms < until: return spawn, travel
    return 5,10

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
    el,wt = [],[]
    for item in ITEMS:
        w = dist[item]
        if w<=0 or item==no_rep: continue
        if item=="heart" and (hp>=3 or not heart_ok): continue
        if item=="trap" and not last: continue
        el.append(item); wt.append(w)
    if not el:
        for item in ITEMS:
            w = dist[item]
            if w<=0: continue
            if item=="heart" and (hp>=3 or not heart_ok): continue
            if item=="trap" and not last: continue
            el.append(item); wt.append(w)
    rem = fv * sum(wt)
    for i,w in enumerate(wt):
        rem -= w
        if rem < 0: return el[i]
    return el[-1]

def run_test(phone, max_moves, target_duration, min_react=215.0, label=""):
    S = make_s()
    if not load_session(S, phone): return None, None, None

    r = api(S,"GET","/api/thunder-trail/me")
    if r.status_code == 401:
        ref = api(S,"POST","/api/auth/refresh")
        if ref.status_code == 200:
            json.dump([{"name":c.name,"value":c.value} for c in S.cookies],
                      open(os.path.join(HERE,f".session_{phone}.json"),"w"),indent=2)
            r = api(S,"GET","/api/thunder-trail/me")

    me = r.json().get("data",{}) if r.status_code==200 else {}
    plays = me.get("plays_remaining",0)
    if plays <= 0:
        print(f"  [{label}] {phone} — NO PLAYS LEFT")
        return None, None, None

    r = api(S,"POST","/api/thunder-trail/sessions",{})
    if r.status_code not in (200,201):
        print(f"  [{label}] {phone} — session open FAILED: {r.text[:60]}")
        return None, None, None

    d = r.json()["data"]
    sid, token, seed = d["session_id"], d["session_token"], d.get("seed",0)
    floats = decrypt_drip(sid, d.get("drip_enc",""))

    hp=3; score=0; nxt=0.0; bid=1; combo=0; max_combo=0
    hits={}; last_types=[]; log=[]; cursor=0; committed=0
    heart_gate={"boxes":0,"traps":0,"others":0,"hp_last":3}; pending_hg=None
    t0=time.time(); last_hb=t0

    while True:
        elapsed = time.time()-t0
        if hp<=0 or len(log)>=max_moves or elapsed>=target_duration: break
        gms = elapsed*1000.0
        rem_boxes=(len(floats)-cursor)//2
        if rem_boxes<15:
            fb=cursor//2
            rr=api(S,"POST",f"/api/thunder-trail/sessions/{sid}/drip-refill",{"session_token":token,"from_box":fb})
            if rr.status_code==200:
                rd=rr.json(); nf=decrypt_drip(sid,rd.get("drip_enc"))
                fb2=rd.get("drip_from_box",fb); ti=2*fb2
                if ti>len(floats): floats.extend([0.5]*(ti-len(floats)))
                floats[ti:ti+len(nf)]=nf
        if gms<nxt:
            time.sleep(min(0.02,(nxt-gms)/1000.0)); continue
        spawn_ms=nxt; sp_ev,travel=get_tier(spawn_ms); nxt+=sp_ev
        if cursor>=len(floats): break
        fv_t=floats[cursor]; cursor+=1
        if cursor>=len(floats): break
        fv_d=floats[cursor]; cursor+=1
        if hp<heart_gate["hp_last"]:
            heart_gate={"boxes":0,"traps":0,"others":0,"hp_last":hp}; pending_hg=None
        elif pending_hg is not None:
            if pending_hg=="heart": heart_gate={"boxes":0,"traps":0,"others":0,"hp_last":hp}
            elif pending_hg=="trap": heart_gate["boxes"]+=1; heart_gate["traps"]+=1
            else: heart_gate["boxes"]+=1; heart_gate["others"]+=1
            pending_hg=None
        heart_gate["hp_last"]=hp
        heart_ok=heart_gate["boxes"]>=7 and heart_gate["traps"]>=2 and heart_gate["others"]>=3
        btype=pick_type(fv_t,hp,last_types,heart_ok); barrow=DIRS[int(fv_d*4)]
        pending_hg=btype; last_types.append(btype)
        if len(last_types)>2: last_types.pop(0)
        pct=random.uniform(0.42,0.60)
        react=max(min_react,travel*pct+random.gauss(0,10))
        swipe_at=spawn_ms+react
        if btype in ("thunder","thunder2","gully","firefox"):
            swipe_dir=barrow; score+=SCORING[btype]; combo+=1; max_combo=max(max_combo,combo)
            hits[btype]=hits.get(btype,0)+1
        elif btype=="trap":
            swipe_dir=OPP[barrow]; combo+=1; max_combo=max(max_combo,combo)
            hits["trap"]=hits.get("trap",0)+1
        else:
            swipe_dir=barrow
            if hp<3: hp+=1
            combo+=1; max_combo=max(max_combo,combo); hits["heart"]=hits.get("heart",0)+1
        now=time.time(); wait=t0+swipe_at/1000.0-now
        if wait>0: time.sleep(wait)
        log.append({"boxId":bid,"dir":swipe_dir,"atMs":round(swipe_at,1),"spawnAtMs":round(spawn_ms,1)}); bid+=1
        now=time.time()
        if now-last_hb>=4.8:
            delta=[{"boxId":e["boxId"],"dir":e["dir"],"atMs":e["atMs"],"spawnAtMs":e["spawnAtMs"]} for e in log[committed:]]
            hr=api(S,"POST",f"/api/thunder-trail/sessions/{sid}/heartbeat",
                   {"session_token":token,"boxes_seen":len(log),"score_so_far":score,
                    "paused":False,"at_ms":round(swipe_at,1),"boxes_committed":len(log),
                    "chain_hash":chain_hash(sid,log),"input_log_delta":delta})
            if hr.status_code==200: committed=len(log); last_hb=now

    if not log: return None, None, None

    dur=log[-1]["atMs"]+random.uniform(280,420)
    bc={CMAP.get(k,k):v for k,v in hits.items()}
    delta_fin=[{"boxId":e["boxId"],"dir":e["dir"],"atMs":e["atMs"],"spawnAtMs":e["spawnAtMs"]} for e in log[committed:]]
    api(S,"POST",f"/api/thunder-trail/sessions/{sid}/heartbeat",
        {"session_token":token,"boxes_seen":len(log),"score_so_far":score,
         "paused":False,"at_ms":round(dur,1),"boxes_committed":len(log),
         "chain_hash":chain_hash(sid,log),"input_log_delta":delta_fin})

    jr=api(S,"POST",f"/api/thunder-trail/sessions/{sid}/journey",
           {"session_token":token,"seed":seed,"input_log":log,"final_score":score,
            "duration_ms":round(dur,1),"max_combo":max_combo,"hit_counts":bc,
            "max_tier_reached":get_tier_idx(dur)+1})
    final_score=score
    try:
        jd=jr.json().get("data",{})
        if jd.get("recomputed_score") is not None: final_score=jd["recomputed_score"]
    except: pass

    sr=api(S,"POST",f"/api/thunder-trail/sessions/{sid}/score",
           {"session_token":token,"final_score":final_score,"duration_ms":round(dur,1),
            "max_combo":max_combo,"box_counts":bc,"seed":seed,"input_log":log})
    res=sr.json().get("data",{})
    is_bot=res.get("is_bot"); status=res.get("status")
    return final_score, is_bot, len(log)

def main():
    sessions = json.load(open(os.path.join(HERE,"valid_active_sessions.json")))
    phones = [row[0] for row in sessions]

    print("\n" + "="*65)
    print("  BOUNDARY FINDER — Testing move count and duration limits")
    print("="*65)

    # ── PHASE 1: Move count boundary (duration fixed at 93.5s) ──────
    move_tests = [166, 167, 168, 169, 170, 171, 172]
    print("\n📊 PHASE 1: Move count boundary (duration=93.5s fixed)")
    print(f"  {'Moves':>6} | {'Phone':>12} | {'Score':>6} | {'is_bot':>8} | {'Verdict'}")
    print("  " + "-"*55)

    move_results = []
    phone_idx = 0
    for moves in move_tests:
        if phone_idx >= len(phones): break
        phone = phones[phone_idx]; phone_idx += 1
        score, is_bot, actual_moves = run_test(phone, moves, 93.5, 215.0, f"MOVES-{moves}")
        if score is None:
            # try next phone
            if phone_idx < len(phones):
                phone = phones[phone_idx]; phone_idx += 1
                score, is_bot, actual_moves = run_test(phone, moves, 93.5, 215.0, f"MOVES-{moves}")
        verdict = "✅ CLEAN" if is_bot==False else ("🤖 BOT" if is_bot==True else "⚠️ NONE")
        print(f"  {moves:>6} | {phone:>12} | {score or 0:>6} | {str(is_bot):>8} | {verdict}")
        move_results.append((moves, phone, score, is_bot))
        time.sleep(2)

    # ── PHASE 2: Duration boundary (moves fixed at 165) ─────────────
    dur_tests = [95.0, 96.0, 97.0, 98.0, 100.0]
    print(f"\n📊 PHASE 2: Duration boundary (moves=165 fixed)")
    print(f"  {'DurS':>6} | {'Phone':>12} | {'Score':>6} | {'is_bot':>8} | {'Verdict'}")
    print("  " + "-"*55)

    dur_results = []
    for dur in dur_tests:
        if phone_idx >= len(phones): break
        phone = phones[phone_idx]; phone_idx += 1
        score, is_bot, actual_moves = run_test(phone, 165, dur, 215.0, f"DUR-{dur}")
        if score is None:
            if phone_idx < len(phones):
                phone = phones[phone_idx]; phone_idx += 1
                score, is_bot, actual_moves = run_test(phone, 165, dur, 215.0, f"DUR-{dur}")
        verdict = "✅ CLEAN" if is_bot==False else ("🤖 BOT" if is_bot==True else "⚠️ NONE")
        print(f"  {dur:>6.1f} | {phone:>12} | {score or 0:>6} | {str(is_bot):>8} | {verdict}")
        dur_results.append((dur, phone, score, is_bot))
        time.sleep(2)

    # ── SUMMARY ─────────────────────────────────────────────────────
    print("\n" + "="*65)
    print("  BOUNDARY FINDINGS")
    print("="*65)
    print("\nMove count results:")
    for moves, phone, score, is_bot in move_results:
        verdict = "✅ SAFE" if is_bot==False else "🚫 BLOCKED"
        print(f"  {moves} moves → {verdict} (score={score})")

    print("\nDuration results:")
    for dur, phone, score, is_bot in dur_results:
        verdict = "✅ SAFE" if is_bot==False else "🚫 BLOCKED"
        print(f"  {dur}s → {verdict} (score={score})")

    # find highest safe move count
    safe_moves = [m for m,p,s,b in move_results if b==False]
    safe_durs  = [d for d,p,s,b in dur_results  if b==False]
    if safe_moves:
        print(f"\n🎯 Highest safe move count: {max(safe_moves)} moves")
    if safe_durs:
        print(f"🎯 Highest safe duration:   {max(safe_durs)}s")
    print("="*65)

if __name__ == "__main__":
    main()
