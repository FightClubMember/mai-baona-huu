import base64, hashlib, hmac, json, os, random, sys, time, threading
from queue import PriorityQueue, Empty
import requests, websocket

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception: pass

BASE = "https://thunder-zone.coke2home.com"
WS_URL = "wss://thunder-zone.coke2home.com/backend/api/v1/thunder-trails/ws"
HERE = os.path.dirname(os.path.abspath(__file__))

OPP = {"up": "down", "down": "up", "left": "right", "right": "left"}

def sign_msg(session_id, key_bytes, t, seq, ts, p):
    if t == "hello":
        p_str = f"{p.get('ticket','')}|{p.get('resume_from_seq',0)}"
    elif t == "ready":
        p_str = ""
    elif t == "swipe":
        p_str = f"{p.get('box_id',0)}|{p.get('dir','')}|{p.get('client_at_ms',0)}"
    elif t == "pong":
        p_str = f"{p.get('nonce','')}"
    else:
        p_str = ""
    
    raw_str = f"{session_id}|{seq}|{ts}|{t}|{p_str}"
    sig = base64.b64encode(hmac.new(key_bytes, raw_str.encode(), hashlib.sha256).digest()).decode()
    return sig

def play_websocket_game(phone, target_score=2680):
    s = requests.Session()
    fpath = os.path.join(HERE, f".session_{phone}.json")
    if not os.path.exists(fpath):
        print(f"[{phone}] ❌ Session file not found")
        return False

    raw_cookies = json.load(open(fpath))
    cookie_dict = {}
    for c in raw_cookies:
        cookie_dict[c["name"]] = c["value"]
        s.cookies.set(c["name"], c["value"])

    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9,hi;q=0.8",
        "content-type": "application/json",
        "origin": BASE,
        "referer": f"{BASE}/game?skipWin=1",
        "sec-ch-ua": '"Chromium";v="154", "Google Chrome";v="154", "Not A(Brand";v="99"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": '"Android"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36",
        "x-botd": "human"
    }
    s.headers.update(headers)

    # 1. Check /me & refresh if needed
    r = s.get(BASE + "/api/thunder-trail/me", timeout=8)
    if r.status_code == 401:
        ref = s.post(BASE + "/api/auth/refresh", timeout=8)
        if ref.status_code == 200:
            for c in s.cookies:
                cookie_dict[c.name] = c.value
            json.dump([{"name": k, "value": v} for k, v in cookie_dict.items()], open(fpath, "w"), indent=2)
            r = s.get(BASE + "/api/thunder-trail/me", timeout=8)

    if r.status_code != 200:
        print(f"[{phone}] ❌ /me endpoint failed: {r.text}")
        return False

    me = r.json().get("data", {})
    username = me.get("username", "N/A")
    plays = me.get("plays_remaining", 0)
    is_blocked = me.get("is_blocked", False)

    print(f"\n{'='*65}")
    print(f"🏆 TOP 20 CONQUEST: {phone} ({username}) | Plays: {plays} | Target: {target_score} pts")
    print(f"{'='*65}")

    if is_blocked:
        print("❌ Account is blocked.")
        return False

    if plays <= 0:
        print("⚠️ 0 plays remaining.")
        return False

    # 2. Start session
    r_sess = s.post(BASE + "/api/thunder-trail/sessions", json={}, timeout=10)
    if r_sess.status_code not in (200, 201):
        print(f"❌ Session init failed: {r_sess.text}")
        return False

    sd = r_sess.json().get("data", {})
    sid = sd.get("session_id")
    ticket = sd.get("socket_ticket")
    frame_key = sd.get("frame_key")

    if not sid or not ticket or not frame_key:
        print(f"❌ Missing socket ticket or frame key: {sd}")
        return False

    key_bytes = base64.b64decode(frame_key)
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])

    # 3. Connect to WebSocket
    ws = websocket.create_connection(
        WS_URL,
        timeout=10,
        origin=BASE,
        header=[
            "User-Agent: Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36",
            "Accept-Language: en-US,en;q=0.9,hi;q=0.8",
            f"Cookie: {cookie_str}"
        ]
    )

    t0 = time.time()
    def now_ms(): return int((time.time() - t0) * 1000)

    seq_lock = threading.Lock()
    seq = 0

    def send_signed(m_type, p, explicit_ts=None):
        nonlocal seq
        with seq_lock:
            seq += 1
            ts = explicit_ts if explicit_ts is not None else now_ms()
            if m_type == "swipe":
                p["client_at_ms"] = ts
            mac = sign_msg(sid, key_bytes, m_type, seq, ts, p)
            payload = {"v": 1, "t": m_type, "seq": seq, "ts": ts, "p": p, "mac": mac}
            try: ws.send(json.dumps(payload))
            except Exception: pass

    send_signed("hello", {"session_id": sid, "ticket": ticket})
    send_signed("ready", {})

    current_score = 0
    current_hp = 3
    active_boxes = {}
    resolved_boxes = set()
    game_running = True
    stop_swiping = False

    # Thread-safe Heap Priority Queue for ordered network dispatch
    import heapq
    outgoing_heap = []
    heap_lock = threading.Lock()
    counter = 0

    def schedule_msg(m_type, p, send_at_time, explicit_ts=None):
        nonlocal counter
        with heap_lock:
            counter += 1
            heapq.heappush(outgoing_heap, (send_at_time, counter, m_type, p, explicit_ts))

    def sender_worker():
        while game_running:
            item_to_send = None
            with heap_lock:
                if outgoing_heap:
                    send_at_time, c, m_type, p, explicit_ts = outgoing_heap[0]
                    now = time.time()
                    if now >= send_at_time:
                        heapq.heappop(outgoing_heap)
                        item_to_send = (m_type, p, explicit_ts)

            if item_to_send:
                m_type, p, explicit_ts = item_to_send
                if game_running:
                    ts = explicit_ts if explicit_ts is not None else now_ms()
                    send_signed(m_type, p, explicit_ts=ts)
            else:
                time.sleep(0.003)

    t_sender = threading.Thread(target=sender_worker, daemon=True)
    t_sender.start()

    while game_running and current_hp > 0:
        try:
            raw = ws.recv()
            if not raw: break
            msg = json.loads(raw)
            m_type = msg.get("t")
            m_p = msg.get("p", {})

            if m_type == "welcome":
                current_hp = m_p.get("hp", 3)
                current_score = m_p.get("score", 0)
                print(f"🔥 Live WS Connected & Handshake OK! HP: {current_hp} | Score: {current_score}")

            elif m_type == "ping":
                nonce = m_p.get("nonce")
                pong_at = time.time() + random.uniform(0.015, 0.035)
                schedule_msg("pong", {"nonce": nonce}, pong_at)

            elif m_type == "spawn":
                bid = m_p.get("box_id")
                btype = m_p.get("type")
                travel = m_p.get("travel_ms", 1950)
                spawn_at_ms = m_p.get("spawn_at_ms", 0)
                arrow = m_p.get("arrow")
                active_boxes[bid] = {"type": btype, "travel": travel, "spawn_at_ms": spawn_at_ms, "arrow": arrow, "t_spawn": time.time(), "scheduled": False}

                if not stop_swiping:
                    if arrow or travel <= 300:
                        active_boxes[bid]["scheduled"] = True
                        if travel <= 300:
                            prog = random.uniform(0.38, 0.42)
                            send_time = time.time()
                            predicted_arrow = arrow if arrow else random.choice(["up", "right", "down", "left"])
                            swipe_dir = "left" if btype == "trap" else predicted_arrow
                        elif travel >= 1200:
                            prog = random.uniform(0.54, 0.64)
                            send_time = max(time.time(), active_boxes[bid]["t_spawn"] + (travel * prog) / 1000.0)
                            swipe_dir = OPP.get(arrow, "left") if btype == "trap" else arrow
                        elif travel >= 800:
                            prog = random.uniform(0.46, 0.54)
                            send_time = max(time.time(), active_boxes[bid]["t_spawn"] + (travel * prog) / 1000.0)
                            swipe_dir = OPP.get(arrow, "left") if btype == "trap" else arrow
                        else:
                            prog = random.uniform(0.36, 0.42)
                            send_time = max(time.time(), active_boxes[bid]["t_spawn"] + (travel * prog) / 1000.0)
                            swipe_dir = OPP.get(arrow, "left") if btype == "trap" else arrow

                        explicit_ts = spawn_at_ms + int(travel * prog)
                        schedule_msg("swipe", {"box_id": bid, "dir": swipe_dir}, send_time, explicit_ts=explicit_ts)

            elif m_type == "reveal":
                bid = m_p.get("box_id")
                arrow = m_p.get("arrow")
                if bid in active_boxes:
                    active_boxes[bid]["arrow"] = arrow

                if stop_swiping:
                    continue

                box_info = active_boxes.get(bid, {})
                if box_info.get("scheduled"):
                    continue

                box_info["scheduled"] = True
                btype = box_info.get("type", "thunder")
                travel = box_info.get("travel", 1950)
                spawn_at_ms = box_info.get("spawn_at_ms", 0)

                if travel >= 1200:
                    prog = random.uniform(0.54, 0.64)
                    send_time = max(time.time(), box_info["t_spawn"] + (travel * prog) / 1000.0)
                elif travel >= 800:
                    prog = random.uniform(0.46, 0.54)
                    send_time = max(time.time(), box_info["t_spawn"] + (travel * prog) / 1000.0)
                elif travel >= 500:
                    prog = random.uniform(0.40, 0.48)
                    send_time = max(time.time(), box_info["t_spawn"] + (travel * prog) / 1000.0)
                else:
                    prog = random.uniform(0.42, 0.52)
                    send_time = time.time()

                explicit_ts = spawn_at_ms + int(travel * prog)
                swipe_dir = OPP.get(arrow, "left") if btype == "trap" else arrow
                schedule_msg("swipe", {"box_id": bid, "dir": swipe_dir}, send_time, explicit_ts=explicit_ts)

            elif m_type == "result":
                bid = m_p.get("box_id")
                outcome = m_p.get("outcome")
                pts = m_p.get("points", 0)
                current_score = m_p.get("score", current_score)
                current_hp = m_p.get("hp", current_hp)
                resolved_boxes.add(bid)

                if outcome == "correct":
                    print(f"  ⚡ Box #{bid} ({active_boxes.get(bid,{}).get('type')}) -> +{pts} pts | Score: {current_score} | HP: {current_hp}")
                elif outcome == "avoided":
                    print(f"  🛡️ Box #{bid} (trap) -> avoided | Score: {current_score} | HP: {current_hp}")
                elif outcome == "healed":
                    print(f"  ❤️ Box #{bid} (heart) -> healed | Score: {current_score} | HP: {current_hp}")
                else:
                    print(f"  ❌ Box #{bid} -> {outcome} | Score: {current_score} | HP: {current_hp}")

                if current_score >= target_score and not stop_swiping:
                    print(f"\n🏆 TARGET SCORE REACHED ({current_score} pts >= {target_score})! Natural exit: letting remaining boxes finish.")
                    stop_swiping = True

            elif m_type == "end":
                fin = m_p.get("final_score", current_score)
                is_bot = m_p.get("is_bot")
                reason = m_p.get("reason")
                print(f"\n🏁 SERVER GAME COMPLETED! Final Score: {fin} | is_bot: {is_bot} | reason: {reason}")
                game_running = False
                break

        except Exception as e:
            print(f"WS Exception: {e}")
            break

    try: ws.close()
    except: pass

    time.sleep(2.0)
    lb = s.get(BASE + "/api/thunder-trail/sub-leaderboard")
    if lb.status_code == 200:
        lbd = lb.json().get("data", {})
        print(f"\n🏆 FINAL LEADERBOARD RANK: #{lbd.get('me_rank')} | Score: {lbd.get('me_score')} pts")

    return True

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else "7623087415"
    target = int(sys.argv[2]) if len(sys.argv) > 2 else 2680
    play_websocket_game(p, target_score=target)
