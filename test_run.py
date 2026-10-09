import json, os, random, sys, time, nabab

def run_test(phone):
    if not nabab.load_session(phone) or nabab.authed() != phone:
        print(f"Session invalid for {phone}")
        return

    me = nabab.api("GET","/api/thunder-trail/me").json().get("data",{})
    print(f"\n==============================================")
    print(f"  Testing Target Score 3400+ (No-Ban)")
    print(f"==============================================")
    print(f"  Mobile     : {phone}")
    print(f"  Username   : {me.get('username')}")
    print(f"  Plays Left : {me.get('plays_remaining')} / 5")

    if me.get("plays_remaining", 0) == 0:
        print("No plays left today for this account.")
        return

    min_duration = 84.0
    max_duration = 86.5
    
    print(f"\nAuto-running test session. Target score: ~3450 (Rank #12-#18) | Stop at ~{min_duration}s or HP=0.\n")

    time.sleep(random.uniform(1.2, 2.5))
    r = nabab.api("POST","/api/thunder-trail/sessions",{})
    if r.status_code not in (200,201): 
        sys.exit(f"Session open failed: {r.text}")
    d = r.json()["data"]
    sid, token = d["session_id"], d["session_token"]
    seed = d.get("seed", 0)
    print(f"Session ID: {sid[:12]}... | Seed: {seed}")

    floats = nabab.decrypt_drip(sid, d.get("drip_enc",""))
    print(f"Floats decrypted: {len(floats)} ({len(floats)//2} boxes)")

    time.sleep(random.uniform(2.0, 3.5))

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
            rr = nabab.api("POST", f"/api/thunder-trail/sessions/{sid}/drip-refill",
                          {"session_token":token,"from_box":fb})
            if rr.status_code == 200:
                rd = rr.json()
                nf = nabab.decrypt_drip(sid, rd.get("drip_enc"))
                fb2 = rd.get("drip_from_box", fb)
                ti = 2 * fb2
                if ti > len(floats): floats.extend([0.5]*(ti-len(floats)))
                floats[ti:ti+len(nf)] = nf

        if gms < nxt:
            time.sleep(min(0.04, (nxt-gms)/1000.0))
            continue

        spawn_ms = nxt
        sp_ev, travel = nabab.get_tier(spawn_ms)
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

        btype  = nabab.pick_type(fv_t, hp, last_types, heart_ok)
        barrow = nabab.DIRS[int(fv_d * 4)]

        pending_hg = btype
        last_types.append(btype)
        if len(last_types) > 2: last_types.pop(0)

        swipe_at = spawn_ms + nabab.reaction_ms(travel) + random.uniform(-10, 10)

        # Deterministic clean play for replay verification alignment
        if btype in ("thunder","thunder2","gully","firefox"):
            swipe_dir = barrow
            score += nabab.SCORING[btype]
            combo += 1; max_combo = max(max_combo, combo)
            hits[btype] = hits.get(btype,0) + 1
        elif btype == "trap":
            swipe_dir = nabab.OPP[barrow]
            combo += 1; max_combo = max(max_combo, combo)
            hits["trap"] = hits.get("trap",0) + 1
        else: # heart
            swipe_dir = barrow
            if hp < 3: hp += 1
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
                      "chain_hash":nabab.chain_hash(sid,log),"input_log_delta":delta}
            hr = nabab.api("POST",f"/api/thunder-trail/sessions/{sid}/heartbeat",hb_pay)
            if hr.status_code == 200:
                hb_n += 1; committed = len(log); last_hb = now

        sys.stdout.write(f"\r Score: {score} | HP: {hp}/3 | Box: #{bid-1} | Combo: {combo} | HB: #{hb_n} ")
        sys.stdout.flush()

    dur = (time.time() - t0) * 1000.0
    if log: dur = log[-1]["atMs"] + random.uniform(280, 480)

    print(f"\n\nLocal Score: {score} | Moves: {len(log)} | Max Combo: {max_combo} | Dur: {dur/1000:.1f}s")

    bc = {}
    for k,v in hits.items():
        mk = nabab.CMAP.get(k,k); bc[mk] = bc.get(mk,0) + v

    # Final Journey submit
    jr_pay = {"session_token":token,"seed":seed,"input_log":log,"final_score":score,
              "duration_ms":round(dur,1),"max_combo":max_combo,"hit_counts":bc,
              "max_tier_reached":nabab.get_tier_idx(dur)+1}
    jr = nabab.api("POST",f"/api/thunder-trail/sessions/{sid}/journey",jr_pay)
    print(f"[Journey Status] {jr.status_code} | {jr.text}")

    final_submit_score = score
    try:
        jd = jr.json().get("data",{})
        if "recomputed_score" in jd and jd["recomputed_score"] is not None:
            final_submit_score = jd["recomputed_score"]
            print(f"[Server Sync] Server Recomputed Score: {final_submit_score}")
    except Exception as e:
        print(f"[Sync Error] {e}")

    # Final Score submit
    sc_pay = {"session_token":token,"final_score":final_submit_score,"duration_ms":round(dur,1),
              "max_combo":max_combo,"box_counts":bc,"seed":seed,"input_log":log}
    sr = nabab.api("POST",f"/api/thunder-trail/sessions/{sid}/score",sc_pay)
    print(f"[Score Status]   {sr.status_code} | {sr.text}")

if __name__ == "__main__":
    run_test("6005987915")
