#!/usr/bin/env python3
"""
run_all_nabab.py — Automated Multi-Account Runner for Thunder Trail (nabab.py engine).

Features:
1. Loads all active device numbers from device_index.json.
2. Reuses saved sessions (.session_{phone}.json) or auto-logs in via Firebase OTP.
3. If an account fails (blocked, rate-limited, OTP timeout), logs clear failure reasons.
4. Auto-runs the nabab.py AES-GCM drip decryption game engine for devices with plays remaining.
5. Displays & records High Score, Sub-Leaderboard Rank, and Top 30 positions.
6. Optional proxy rotation fallback on HTTP 429 rate-limiting.
7. Saves comprehensive results to thunder_nabab_results.txt and thunder_nabab_leaderboard.txt.
"""

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import hashlib
import hmac
import json
import os
import random
import re
import sys
import time
from typing import Dict, List, Optional, Tuple
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Windows UTF-8 console & unbuffered output fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        pass

# Paths
DIR_PATH = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\stocks\device_index.json"
RESULTS_FILE = os.path.join(DIR_PATH, "thunder_nabab_results.txt")
LEADERBOARD_FILE = os.path.join(DIR_PATH, "thunder_nabab_leaderboard.txt")
RANKED_RESULTS_FILE = os.path.join(DIR_PATH, "thunder_ranked_results.txt")

# Game Constants
BASE = "https://thunder-zone.coke2home.com"
TU = base64.b64decode("a9rc/DSXunC5PdkYlDB6KkX/evwfSTDUD8PQdaepxe0=")
SCORING = {"thunder": 15, "thunder2": 15, "gully": 50, "firefox": 50, "heart": 0, "trap": 0}
DIST_FULL = {"thunder": 0.2, "thunder2": 0.2, "heart": 0, "trap": 0.45, "gully": 0.075, "firefox": 0.075}
DIST_DMG = {"thunder": 0.175, "thunder2": 0.175, "heart": 0.2, "trap": 0.3, "gully": 0.075, "firefox": 0.075}
ITEMS = ["thunder", "thunder2", "heart", "trap", "gully", "firefox"]
DIRS = ["up", "down", "left", "right"]
OPP = {"up": "down", "down": "up", "left": "right", "right": "left"}
CMAP = {"thunder": "thunder_box", "thunder2": "thunder_box", "thunderCan": "thunder_can",
        "gully": "gully_labs", "firefox": "firefox", "heart": "heart", "trap": "trap"}
TIERS = [
    (15000, 1000, 1950), (30000, 800, 1540), (45000, 700, 1350), (60000, 600, 1150),
    (75000, 500, 963), (90000, 400, 770), (105000, 200, 385), (120000, 100, 193),
    (135000, 50, 96), (150000, 20, 39), (165000, 10, 19), (180000, 5, 10), (float("inf"), 5, 10)
]

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": BASE,
    "Referer": f"{BASE}/game",
    "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
}

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/zevtyardt/proxy-list/main/http.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/Zaeem20/FREE_PROXIES_LIST/master/http.txt",
    "https://raw.githubusercontent.com/mmpx12/proxy-list/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt"
]

LIVE_PROXIES: List[str] = []


def load_live_proxies() -> list:
    global LIVE_PROXIES
    if LIVE_PROXIES:
        return LIVE_PROXIES
    import os
    proxy_file = os.path.join(DIR_PATH, "valid_proxies.txt")
    if os.path.exists(proxy_file):
        with open(proxy_file, "r") as f:
            LIVE_PROXIES = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(LIVE_PROXIES)} WORKING proxies from valid_proxies.txt.", flush=True)
    else:
        print("No valid_proxies.txt found!", flush=True)
        LIVE_PROXIES = []
    return LIVE_PROXIES
    print("🌐 Loading proxy list for rate-limit protection...", flush=True)
    proxies = set()
    for src in PROXY_SOURCES:
        try:
            r = requests.get(src, timeout=3)
            if r.status_code == 200:
                lines = [line.strip() for line in r.text.splitlines() if ":" in line]
                proxies.update([f"http://{p}" if not p.startswith("http") else p for p in lines[:100]])
        except Exception:
            pass
    LIVE_PROXIES = list(proxies)
    print(f"✅ Loaded {len(LIVE_PROXIES)} proxies for fallback rotation.", flush=True)
    return LIVE_PROXIES


def get_random_proxy() -> Optional[str]:
    if LIVE_PROXIES:
        return random.choice(LIVE_PROXIES)
    return None


def fetch_firebase_otp(panel_url: str, client_id: str, existing_keys: Optional[set] = None, min_ts: int = 0, timeout_sec: int = 25) -> Optional[str]:
    """Polls Firebase messages for fresh Coke/Thunder 6-digit OTP."""
    if not panel_url or not client_id:
        return None
    url = f"{panel_url.rstrip('/')}/messages/{client_id}.json"
    start_time = time.time()
    cutoff_ts = max(0, min_ts - 60000)

    while time.time() - start_time < timeout_sec:
        try:
            r = requests.get(url, timeout=4)
            if r.status_code == 200 and r.json():
                msgs = r.json()
                if isinstance(msgs, dict):
                    sorted_keys = sorted(
                        msgs.keys(),
                        key=lambda k: int(k) if str(k).isdigit() else 0,
                        reverse=True
                    )
                    for k in sorted_keys:
                        mdata = msgs[k]
                        if not isinstance(mdata, dict):
                            continue

                        # If key is epoch timestamp ms, check cutoff
                        if str(k).isdigit() and len(str(k)) >= 12:
                            k_num = int(k)
                            if cutoff_ts > 0 and k_num < cutoff_ts:
                                continue
                        elif existing_keys is not None and k in existing_keys:
                            continue

                        sender = str(mdata.get("sender") or "").upper()
                        txt = str(mdata.get("body") or mdata.get("message") or mdata.get("text") or "")

                        # Filter for Thums Up / Coke SMS
                        is_thums = any(w in sender for w in ("THMSUP", "THUMSUP", "COKE", "C2H")) or \
                                   any(w in txt.lower() for w in ("thums up", "thunder zone", "thunder trail", "coke2home"))

                        if is_thums or ("otp" in txt.lower() and not any(w in txt.lower() for w in ("fetch", "phonepe", "swiggy", "zomato", "bank", "icici", "hdfc", "sbi", "airtel"))):
                            m = re.search(r"(?:One Time Password|OTP|code is)\s*[:\-]?\s*(\d{6})", txt, re.IGNORECASE)
                            if m:
                                return m.group(1)
                            m2 = re.search(r"\b(\d{6})\b", txt)
                            if m2:
                                return m2.group(1)
        except Exception:
            pass
        time.sleep(1.8)
    return None


class NababPlayer:
    """Thread-safe automated player encapsulation for a single phone account."""

    def __init__(self, phone: str, device_info: Optional[dict] = None, use_proxy: bool = False):
        self.phone = "".join(c for c in str(phone) if c.isdigit())[-10:]
        self.device_info = device_info or {}
        self.use_proxy = use_proxy
        self.proxy = get_random_proxy() if use_proxy else None
        self.session_file = os.path.join(DIR_PATH, f".session_{self.phone}.json")
        self.s = requests.Session()
        self.s.headers.update(HEADERS)
        if self.proxy:
            self.s.proxies = {"http": self.proxy, "https": self.proxy}

    def api(self, method: str, path: str, body: dict = None) -> requests.Response:
        for i in range(2):
            try:
                r = self.s.request(method, BASE + path, json=body, timeout=8)
                # Auto-refresh on 401
                if r.status_code == 401 and i == 0 and "/auth/" not in path:
                    try:
                        ref = self.s.post(BASE + "/api/auth/refresh", timeout=10)
                        if ref.status_code == 200:
                            self.save_session()
                    except Exception:
                        pass
                    time.sleep(0.5)
                    continue
                return r
            except Exception:
                if i == 1:
                    raise
                time.sleep(0.8)
        return r

    def load_session(self) -> bool:
        possible_paths = [
            self.session_file,
            os.path.join(DIR_PATH, f".cookies_{self.phone}.json"),
            os.path.join(r"C:\Users\Himanshu Kumar\OneDrive\Desktop\h build bot", f".cookies_{self.phone}.json"),
            os.path.join(r"C:\Users\Himanshu Kumar\OneDrive\Desktop\test", f".cookies_{self.phone}.json"),
        ]
        for p in possible_paths:
            if os.path.exists(p):
                try:
                    self.s.cookies.clear()
                    with open(p, "r", encoding="utf-8") as f:
                        cookies = json.load(f)
                    for c in cookies:
                        self.s.cookies.set(c["name"], c["value"])
                    return True
                except Exception:
                    pass
        return False

    def save_session(self):
        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump([{"name": c.name, "value": c.value} for c in self.s.cookies], f, indent=2)
        except Exception:
            pass

    def check_auth(self) -> Optional[str]:
        try:
            r = self.api("GET", "/api/auth/me")
            if r.status_code == 200:
                d = r.json()
                if d.get("success") and d.get("isAuthenticated"):
                    return d["user"].get("phone_number")
            # Try token refresh if 401
            if r.status_code == 401:
                ref = self.s.post(BASE + "/api/auth/refresh", timeout=10)
                if ref.status_code == 200:
                    self.save_session()
                    r2 = self.api("GET", "/api/auth/me")
                    if r2.status_code == 200:
                        d2 = r2.json()
                        if d2.get("success") and d2.get("isAuthenticated"):
                            return d2["user"].get("phone_number")
        except Exception:
            pass
        return None

    def login_with_firebase_otp(self) -> Tuple[bool, str]:
        """Sends OTP and auto-retrieves it from linked Firebase node."""
        panel_url = self.device_info.get("panel_url")
        client_id = self.device_info.get("client_id")

        if not panel_url or not client_id:
            return False, "Missing Firebase panel_url or client_id in device index"

        purl = panel_url.rstrip("/")
        # Snapshot existing message keys before sending OTP
        existing_keys = set()
        try:
            snap = requests.get(f"{purl}/messages/{client_id}.json?shallow=true", timeout=4)
            if snap.status_code == 200 and isinstance(snap.json(), dict):
                existing_keys = set(snap.json().keys())
        except Exception:
            pass

        start_time_ms = int(time.time() * 1000)

        # Step 1: Send OTP
        r = self.api("POST", "/api/auth/send-otp", {"phone_number": self.phone})
        if r.status_code == 403:
            return False, "Account blocked from promotion (Clause 6)"
        if r.status_code == 429:
            return False, "Rate limited on OTP send (429)"
        if r.status_code != 200:
            return False, f"OTP send failed ({r.status_code}): {r.text[:100]}"

        # Step 2: Fetch OTP from Firebase
        otp = fetch_firebase_otp(panel_url, client_id, existing_keys=existing_keys, min_ts=start_time_ms, timeout_sec=25)
        if not otp:
            return False, "OTP not received in Firebase inbox (timeout)"

        # Step 3: Verify OTP
        time.sleep(0.5)
        vr = self.api("POST", "/api/auth/verify-otp", {"phone_number": self.phone, "otp": otp})
        if vr.status_code != 200:
            return False, f"OTP verify failed ({vr.status_code}): {vr.text[:100]}"

        v = vr.json()
        ott = v.get("one_time_token") or (v.get("data") or {}).get("one_time_token")

        if v.get("requiresSignup") or (v.get("data") or {}).get("requiresSignup"):
            import random
            names = ["Rahul", "Rohan", "Priya", "Amit", "Neha", "Vikram", "Sneha", "Karan", "Pooja", "Arjun", "Kavya", "Suresh", "Aditi", "Ravi", "Anjali"]
            random_name = random.choice(names) + str(random.randint(100, 999))
            try:
                self.api("POST", "/api/auth/signup", {
                    "one_time_token": ott,
                    "phone_number": self.phone,
                    "name": random_name
                })
            except Exception:
                pass

        if ott:
            time.sleep(0.4)
            self.api("POST", "/api/auth/validate-token", {"one_time_token": ott})
            time.sleep(0.4)
            self.api("POST", "/api/auth/exchange-token", {"one_time_token": ott})

        self.save_session()
        return True, "Login successful"

    def ensure_authenticated(self) -> Tuple[bool, str]:
        """Loads saved session or logs in."""
        if self.load_session() and self.check_auth() == self.phone:
            return True, "Active session found"
        # Not logged in, attempt login via Firebase
        return self.login_with_firebase_otp()

    def get_profile_and_rank(self) -> dict:
        """Fetches profile score, remaining plays, and current rank."""
        res = {
            "username": "N/A",
            "best_score": 0,
            "plays_remaining": 0,
            "is_blocked": False,
            "me_rank": None,
            "me_score": 0
        }
        try:
            mr = self.api("GET", "/api/thunder-trail/me")
            if mr.status_code == 200:
                md = mr.json().get("data", {})
                res["username"] = md.get("username", "N/A")
                res["best_score"] = md.get("best_score", 0)
                res["plays_remaining"] = md.get("plays_remaining", 0)
                res["is_blocked"] = md.get("is_blocked", False)
        except Exception:
            pass

        try:
            br = self.api("GET", "/api/thunder-trail/sub-leaderboard")
            if br.status_code == 200:
                bd = br.json().get("data", {})
                res["me_rank"] = bd.get("me_rank")
                res["me_score"] = bd.get("me_score", 0)
        except Exception:
            pass

        return res

    def decrypt_drip(self, sid: str, enc: str) -> list:
        if not enc:
            return []
        try:
            raw = base64.b64decode(enc)
            key = hmac.new(TU, sid.encode(), hashlib.sha256).digest()
            return json.loads(AESGCM(key).decrypt(raw[:12], raw[12:], None).decode())
        except Exception:
            return []

    def get_tier(self, ms: float) -> Tuple[int, int]:
        for until, spawn, travel in TIERS:
            if ms < until:
                return spawn, travel
        return 5, 10

    def get_tier_idx(self, ms: float) -> int:
        for i, (until, _, __) in enumerate(TIERS):
            if ms < until:
                return i
        return len(TIERS) - 1

    def pick_type(self, fv: float, hp: int, last: list, heart_ok: bool) -> str:
        dist = DIST_FULL if hp >= 3 else DIST_DMG
        last1 = last[-1] if last else None
        last2 = last[-2] if len(last) >= 2 else None
        no_rep = last1 if last1 == last2 and last1 else None
        first = len(last) == 0
        el, wt = [], []
        for item in ITEMS:
            w = dist[item]
            if w <= 0 or item == no_rep:
                continue
            if item == "heart" and (hp >= 3 or not heart_ok):
                continue
            if item == "trap" and first:
                continue
            el.append(item)
            wt.append(w)
        if not el:
            for item in ITEMS:
                w = dist[item]
                if w <= 0:
                    continue
                if item == "heart" and (hp >= 3 or not heart_ok):
                    continue
                if item == "trap" and first:
                    continue
                el.append(item)
                wt.append(w)
        rem = fv * sum(wt)
        for i, w in enumerate(wt):
            rem -= w
            if rem < 0:
                return el[i]
        return el[-1]

    def reaction_ms(self, travel: int) -> float:
        base = random.uniform(500, 650)
        jitter = random.gauss(0, 20)
        return max(400, base + jitter)

    def chain_hash(self, sid: str, log: list) -> str:
        moves = ",".join(f"{e['boxId']}:{e['dir']}" for e in log)
        return hashlib.sha256(f"{sid}|{moves}".encode()).hexdigest()

    def play_round(self) -> Tuple[bool, int, str]:
        """Runs the complete nabab AES-GCM drip decryption gameplay session."""
        time.sleep(random.uniform(1.0, 2.0))
        r = self.api("POST", "/api/thunder-trail/sessions", {})
        if r.status_code not in (200, 201):
            return False, 0, f"Session create failed ({r.status_code}): {r.text[:100]}"

        d = r.json().get("data", {})
        sid = d.get("session_id")
        token = d.get("session_token")
        seed = d.get("seed", 0)
        if not sid or not token:
            return False, 0, "Missing session_id or token in server response"

        floats = self.decrypt_drip(sid, d.get("drip_enc", ""))
        time.sleep(random.uniform(1.5, 2.5))

        hp = 3
        score, nxt, bid = 0, 0.0, 1
        combo, max_combo = 0, 0
        hits, last_types, log = {}, [], []
        cursor, committed = 0, 0
        heart_gate = {"boxes": 0, "traps": 0, "others": 0, "hp_last": 3}
        pending_hg = None

        min_duration = 91.5
        max_duration = 93.5
        t0 = time.time()
        last_hb = t0
        hb_n = 0

        while True:
            elapsed = time.time() - t0
            if hp <= 0 or elapsed >= max_duration:
                break

            gms = elapsed * 1000.0

            rem_boxes = (len(floats) - cursor) // 2
            if rem_boxes < 15:
                fb = cursor // 2
                rr = self.api("POST", f"/api/thunder-trail/sessions/{sid}/drip-refill",
                              {"session_token": token, "from_box": fb})
                if rr.status_code == 200:
                    rd = rr.json()
                    nf = self.decrypt_drip(sid, rd.get("drip_enc"))
                    fb2 = rd.get("drip_from_box", fb)
                    ti = 2 * fb2
                    if ti > len(floats):
                        floats.extend([0.5] * (ti - len(floats)))
                    floats[ti:ti + len(nf)] = nf

            if gms < nxt:
                time.sleep(min(0.04, (nxt - gms) / 1000.0))
                continue

            spawn_ms = nxt
            sp_ev, travel = self.get_tier(spawn_ms)
            nxt += sp_ev

            if cursor >= len(floats) - 1:
                break
            fv_t = floats[cursor]
            cursor += 1
            fv_d = floats[cursor]
            cursor += 1

            if hp < heart_gate["hp_last"]:
                heart_gate["boxes"] = 0
                heart_gate["traps"] = 0
                heart_gate["others"] = 0
                pending_hg = None
            elif pending_hg is not None:
                if pending_hg == "heart":
                    heart_gate["boxes"] = 0
                    heart_gate["traps"] = 0
                    heart_gate["others"] = 0
                elif pending_hg == "trap":
                    heart_gate["boxes"] += 1
                    heart_gate["traps"] += 1
                else:
                    heart_gate["boxes"] += 1
                    heart_gate["others"] += 1
                pending_hg = None
            heart_gate["hp_last"] = hp
            heart_ok = heart_gate["boxes"] >= 7 and heart_gate["traps"] >= 2 and heart_gate["others"] >= 3

            btype = self.pick_type(fv_t, hp, last_types, heart_ok)
            barrow = DIRS[int(fv_d * 4)]
            pending_hg = btype

            last_types.append(btype)
            if len(last_types) > 2:
                last_types.pop(0)

            swipe_at = spawn_ms + self.reaction_ms(travel) + random.uniform(-15, 15)

            now = time.time()
            wait = t0 + swipe_at / 1000.0 - now
            if wait > 0:
                time.sleep(wait)

            if btype in ("thunder", "thunder2", "gully", "firefox"):
                swipe_dir = barrow
                score += SCORING[btype]
                combo += 1
                max_combo = max(max_combo, combo)
                hits[btype] = hits.get(btype, 0) + 1
            elif btype == "trap":
                swipe_dir = OPP[barrow]
                combo += 1
                max_combo = max(max_combo, combo)
                hits["trap"] = hits.get("trap", 0) + 1
            else:
                swipe_dir = barrow
                if hp < 3:
                    hp += 1
                combo += 1
                max_combo = max(max_combo, combo)
                hits["heart"] = hits.get("heart", 0) + 1

            log.append({"boxId": bid, "dir": swipe_dir, "atMs": round(swipe_at, 1),
                        "spawnAtMs": round(spawn_ms, 1)})
            bid += 1

            now = time.time()
            hb_interval = random.uniform(4.5, 6.5)
            if now - last_hb >= hb_interval:
                delta = [{"boxId": e["boxId"], "dir": e["dir"], "atMs": e["atMs"], "spawnAtMs": e["spawnAtMs"]}
                         for e in log[committed:]]
                hb_pay = {"session_token": token, "boxes_seen": len(log), "score_so_far": score,
                          "paused": False, "at_ms": round(swipe_at, 1), "boxes_committed": len(log),
                          "chain_hash": self.chain_hash(sid, log), "input_log_delta": delta}
                hr = self.api("POST", f"/api/thunder-trail/sessions/{sid}/heartbeat", hb_pay)
                if hr.status_code == 200:
                    hb_n += 1
                    committed = len(log)
                    last_hb = now
                    hd = hr.json()
                    if hd.get("drip_enc"):
                        nf2 = self.decrypt_drip(sid, hd["drip_enc"])
                        fb3 = hd.get("drip_from_box", 0)
                        ti2 = 2 * fb3
                        if ti2 > len(floats):
                            floats.extend([0.5] * (ti2 - len(floats)))
                        floats[ti2:ti2 + len(nf2)] = nf2

        dur = (time.time() - t0) * 1000.0
        if log:
            dur = log[-1]["atMs"] + random.uniform(280, 480)

        bc = {}
        for k, v in hits.items():
            mk = CMAP.get(k, k)
            bc[mk] = bc.get(mk, 0) + v

        delta_fin = [{"boxId": e["boxId"], "dir": e["dir"], "atMs": e["atMs"], "spawnAtMs": e["spawnAtMs"]}
                     for e in log[committed:]]
        self.api("POST", f"/api/thunder-trail/sessions/{sid}/heartbeat", {
            "session_token": token, "boxes_seen": len(log), "score_so_far": score,
            "paused": False, "at_ms": round(dur, 1), "boxes_committed": len(log),
            "chain_hash": self.chain_hash(sid, log), "input_log_delta": delta_fin
        })

        time.sleep(random.uniform(0.5, 1.0))
        sc_pay = {"session_token": token, "final_score": score, "duration_ms": round(dur, 1),
                  "max_combo": max_combo, "box_counts": bc, "seed": seed, "input_log": log}
        sr = self.api("POST", f"/api/thunder-trail/sessions/{sid}/score", sc_pay)

        time.sleep(random.uniform(0.5, 1.0))
        jr_pay = {"session_token": token, "seed": seed, "input_log": log, "final_score": score,
                  "duration_ms": round(dur, 1), "max_combo": max_combo, "hit_counts": bc,
                  "max_tier_reached": self.get_tier_idx(dur) + 1}
        jr = self.api("POST", f"/api/thunder-trail/sessions/{sid}/journey", jr_pay)

        try:
            jd = jr.json().get("data", {})
            if "recomputed_score" in jd and jd["recomputed_score"] != score:
                score = jd["recomputed_score"]
                sc_pay["final_score"] = score
                self.api("POST", f"/api/thunder-trail/sessions/{sid}/score", sc_pay)
        except Exception:
            pass

        return True, score, "Score submitted successfully"


def process_single_account(phone: str, device_info: dict, play_games: bool = True, use_proxy: bool = False) -> dict:
    """Executes authentication, game play, score retrieval, and leaderboard rank for one device."""
    player = NababPlayer(phone, device_info, use_proxy=use_proxy)

    # 1. Authenticate
    ok_auth, auth_msg = player.ensure_authenticated()
    if not ok_auth:
        return {
            "phone": phone,
            "client_id": device_info.get("client_id", "N/A"),
            "panel_url": device_info.get("panel_url", "N/A"),
            "status": "FAIL",
            "reason": auth_msg,
            "score": 0,
            "rank": "N/A",
            "me_rank": None,
            "plays_remaining": 0,
            "username": "N/A"
        }

    # 2. Get initial profile & rank
    prof = player.get_profile_and_rank()
    username = prof.get("username", f"User_{phone[-4:]}")
    best_score = prof.get("best_score", 0)
    plays_remaining = prof.get("plays_remaining", 0)
    me_rank = prof.get("me_rank")

    if prof.get("is_blocked"):
        return {
            "phone": phone,
            "client_id": device_info.get("client_id", "N/A"),
            "panel_url": device_info.get("panel_url", "N/A"),
            "status": "FAIL",
            "reason": "Account is blocked from promotion",
            "score": best_score,
            "rank": f"#{me_rank}" if me_rank else "N/A",
            "me_rank": me_rank,
            "plays_remaining": 0,
            "username": username
        }

    # 3. Play game if enabled and has plays left
    played = False
    game_score = 0
    if play_games and plays_remaining > 0:
        ok_play, g_score, g_msg = player.play_round()
        if ok_play:
            played = True
            game_score = g_score
            time.sleep(1.5)
            # Re-fetch rank after playing
            updated_prof = player.get_profile_and_rank()
            best_score = updated_prof.get("best_score", best_score)
            plays_remaining = updated_prof.get("plays_remaining", plays_remaining - 1)
            me_rank = updated_prof.get("me_rank", me_rank)

    rank_str = f"#{me_rank}" if me_rank else "Not Ranked"
    status_str = f"SUCCESS (Played: {game_score})" if played else "SUCCESS (Checked)"
    if plays_remaining == 0 and not played:
        status_str = "SUCCESS (0 Plays Left)"

    return {
        "phone": phone,
        "client_id": device_info.get("client_id", "N/A"),
        "panel_url": device_info.get("panel_url", "N/A"),
        "status": status_str,
        "reason": "OK",
        "score": best_score,
        "rank": rank_str,
        "me_rank": me_rank,
        "plays_remaining": plays_remaining,
        "username": username
    }


def run_batch(workers: int = 5, play_games: bool = True, limit: Optional[int] = None, use_proxy: bool = False, newest_first: bool = True):
    print("=" * 65, flush=True)
    print("🏆 THUNDER TRAIL (NABAB.PY) AUTOMATED MULTI-DEVICE RUNNER", flush=True)
    print("=" * 65, flush=True)

    if not os.path.exists(INDEX_PATH):
        print(f"❌ device_index.json not found at: {INDEX_PATH}", flush=True)
        return

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        device_index = json.load(f)

    if use_proxy:
        load_live_proxies()

    phones = list(device_index.keys())
    if newest_first:
        phones.reverse()

    if limit:
        phones = phones[:limit]

    print(f"📱 Loaded {len(phones)} unique devices from device_index.json (order: {'Newest First' if newest_first else 'Sequential'})", flush=True)
    print(f"⚙️ Mode: {'Auto-Play & Rank Check' if play_games else 'Rank & Score Fast Scan'}", flush=True)
    print(f"⚡ Concurrent Workers: {workers}", flush=True)
    print(f"🌐 Proxy Rotation: {'Enabled' if use_proxy else 'Direct (Fast)'}", flush=True)
    print("=" * 65, flush=True)

    # Initialize results files
    with open(RESULTS_FILE, "w", encoding="utf-8") as rf:
        rf.write("# Phone | Status | Rank | Best Score | Plays Left | Username | Detail\n")
        rf.write("=" * 75 + "\n")

    completed = 0
    success_count = 0
    fail_count = 0
    all_results = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(process_single_account, p, device_index[p], play_games, use_proxy): p
            for p in phones
        }

        for future in as_completed(future_map):
            completed += 1
            p = future_map[future]
            try:
                res = future.result()
            except Exception as e:
                res = {
                    "phone": p, "client_id": "N/A", "panel_url": "N/A",
                    "status": "FAIL", "reason": f"Exception: {str(e)[:50]}",
                    "score": 0, "rank": "N/A", "me_rank": None,
                    "plays_remaining": 0, "username": "N/A"
                }

            p = res["phone"]
            status = res["status"]
            score = res["score"]
            rank = res["rank"]
            plays = res["plays_remaining"]
            user = res["username"]
            reason = res["reason"]

            if "SUCCESS" in status:
                success_count += 1
                line = f"[{completed}/{len(phones)}] ✅ {p} | Rank: {rank:<12} | Score: {score:<5} | Plays Left: {plays}/5 | User: {user}"
                print(line, flush=True)
                with open(RESULTS_FILE, "a", encoding="utf-8") as rf:
                    rf.write(f"{p} | {status} | {rank} | {score} | {plays} | {user} | {reason}\n")
                all_results.append(res)

                # Dynamically re-write ranked file so live results are always up to date
                cur_success = [r for r in all_results if "SUCCESS" in r.get("status", "")]
                def _sort_key(item):
                    mr = item.get("me_rank")
                    try:
                        if mr is not None and str(mr).strip().isdigit() and int(mr) > 0:
                            return (0, int(mr), -item.get("score", 0))
                    except Exception:
                        pass
                    return (1, -item.get("score", 0), item.get("phone", ""))
                cur_success.sort(key=_sort_key)
                try:
                    with open(RANKED_RESULTS_FILE, "w", encoding="utf-8") as f:
                        f.write("=" * 120 + "\n")
                        f.write(f"🏆 THUNDER TRAIL — SUCCESSFUL ACCOUNTS LEADERBOARD (RANK 1 FIRST) [LIVE: {len(cur_success)} ACCOUNTS]\n")
                        f.write("=" * 120 + "\n")
                        f.write(f"{'Rank':<10} {'Score':<8} {'Phone':<14} {'Device ID (Client ID)':<24} {'Firebase Link (Panel URL)':<50} {'Username':<14}\n")
                        f.write("-" * 120 + "\n")
                        for item in cur_success:
                            f.write(f"{item['rank']:<10} {item['score']:<8} {item['phone']:<14} {item['client_id']:<24} {item['panel_url']:<50} {item['username']:<14}\n")
                        f.write("=" * 120 + "\n")
                except Exception:
                    pass
            else:
                fail_count += 1
                line = f"[{completed}/{len(phones)}] ❌ {p} | FAIL: {reason}"
                print(line, flush=True)
                with open(RESULTS_FILE, "a", encoding="utf-8") as rf:
                    rf.write(f"{p} | FAIL | N/A | 0 | 0 | N/A | {reason}\n")

    # Final Filter ONLY successful entries (DO NOT include failed ones!)
    successful_entries = [r for r in all_results if "SUCCESS" in r.get("status", "")]

    # Sort with Rank 1 first:
    # 1. Accounts with numeric me_rank ascending (Rank 1, 2, 3...)
    # 2. Unranked accounts by score descending
    def rank_sort_key(item):
        mr = item.get("me_rank")
        try:
            if mr is not None and str(mr).strip().isdigit() and int(mr) > 0:
                return (0, int(mr), -item.get("score", 0))
        except Exception:
            pass
        return (1, -item.get("score", 0), item.get("phone", ""))

    successful_entries.sort(key=rank_sort_key)

    # Save dedicated ranked output file with rank 1 first
    for filepath in (RANKED_RESULTS_FILE, LEADERBOARD_FILE):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("=" * 120 + "\n")
            f.write("🏆 THUNDER TRAIL — SUCCESSFUL ACCOUNTS LEADERBOARD (RANK 1 FIRST)\n")
            f.write("=" * 120 + "\n")
            f.write(f"{'Rank':<10} {'Score':<8} {'Phone':<14} {'Device ID (Client ID)':<24} {'Firebase Link (Panel URL)':<50} {'Username':<14}\n")
            f.write("-" * 120 + "\n")
            for item in successful_entries:
                f.write(f"{item['rank']:<10} {item['score']:<8} {item['phone']:<14} {item['client_id']:<24} {item['panel_url']:<50} {item['username']:<14}\n")
            f.write("=" * 120 + "\n")

    print("\n" + "=" * 65, flush=True)
    print("🎉 BATCH RUN COMPLETED!", flush=True)
    print(f"  • Total Devices Processed: {completed}/{len(phones)}", flush=True)
    print(f"  • Successful Accounts:    {success_count}", flush=True)
    print(f"  • Failed Accounts:        {fail_count}", flush=True)
    print(f"  • Ranked In File:         {len(successful_entries)}", flush=True)
    print(f"💾 Ranked Results (No Fails): {RANKED_RESULTS_FILE}", flush=True)
    print(f"💾 Full Status Log:           {RESULTS_FILE}", flush=True)
    print("=" * 65, flush=True)


def main():
    parser = argparse.ArgumentParser(description="Automate nabab.py across all saved device index numbers.")
    parser.add_argument("--workers", type=int, default=5, help="Number of concurrent workers (default: 5)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of devices to process")
    parser.add_argument("--scan-only", action="store_true", help="Only check scores and ranks without playing games")
    parser.add_argument("--proxy", action="store_true", help="Enable proxy rotation")
    parser.add_argument("--phone", type=str, default=None, help="Process a single specific phone number")
    parser.add_argument("--oldest-first", action="store_true", help="Process from oldest to newest (default is newest first)")
    args = parser.parse_args()

    if args.phone:
        p = "".join(c for c in args.phone if c.isdigit())[-10:]
        print(f"Running for single phone: {p}", flush=True)
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            idx = json.load(f)
        info = idx.get(p, {})
        res = process_single_account(p, info, play_games=not args.scan_only, use_proxy=args.proxy)
        print("\nResult:", json.dumps(res, indent=2), flush=True)
    else:
        run_batch(
            workers=args.workers,
            play_games=not args.scan_only,
            limit=args.limit,
            use_proxy=args.proxy,
            newest_first=not args.oldest_first
        )


if __name__ == "__main__":
    main()
