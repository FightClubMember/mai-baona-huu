import json, os, sys, base64, hmac, hashlib

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

HAR_PATH = r"C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (2)\thunder-zone.coke2home.com.har"
data = json.load(open(HAR_PATH, "r", encoding="utf-8"))
entries = data.get("log", {}).get("entries", [])

# Find the session response to get frame_key
frame_key = None
session_id = None
for e in entries:
    req = e.get("request", {})
    res = e.get("response", {})
    if "/api/thunder-trail/sessions" in req.get("url", ""):
        res_text = res.get("content", {}).get("text", "")
        print("Sessions response in HAR:", res_text)
        try:
            d = json.loads(res_text).get("data", {})
            frame_key = d.get("frame_key")
            session_id = d.get("session_id")
        except: pass

print(f"Session ID: {session_id}")
print(f"Frame Key (Base64): {frame_key}")

# Inspect WebSocket messages
for e in entries:
    if "_webSocketMessages" in e:
        msgs = e["_webSocketMessages"]
        print(f"\nTotal WS messages: {len(msgs)}")
        for idx, m in enumerate(msgs[:15]):
            print(f"[{m.get('type')}] {m.get('data')}")

# Test HMAC signature verification
if frame_key:
    key_bytes = base64.b64decode(frame_key)
    print(f"\nDecoded frame_key length: {len(key_bytes)} bytes")
    
    # Test on hello message
    # data: '{"v":1,"t":"hello","seq":1,"ts":435,"p":{"session_id":"9fdee2b8-09f4-4d70-84f3-a794f49aecfb","ticket":"esZu38kIGinO-QuguwsyVA.1791461182188.Xdx647ec7n5os1OK4bk0GmHGHvu8DaD1Zdo1E7zCYL4"},"mac":"Nw9ZONO3BqSe72z19WDXr7/rK1YppvycpPaq060NzLA="}'
    
    # Test permutations of payload signing string:
    hello_p = {"session_id":"9fdee2b8-09f4-4d70-84f3-a794f49aecfb","ticket":"esZu38kIGinO-QuguwsyVA.1791461182188.Xdx647ec7n5os1OK4bk0GmHGHvu8DaD1Zdo1E7zCYL4"}
    expected_mac = "Nw9ZONO3BqSe72z19WDXr7/rK1YppvycpPaq060NzLA="
    
    p_str = json.dumps(hello_p, separators=(',', ':'))
    candidates = [
        f"1|hello|1|435|{p_str}",
        f"hello|1|435|{p_str}",
        f"1|hello|1|435",
        f"hello|1|435",
        f"{session_id}|1|hello|1|435|{p_str}",
        f"1:hello:1:435:{p_str}",
        f"{p_str}",
        f"1|hello|1|{p_str}",
        f"1|hello|{p_str}"
    ]
    for c in candidates:
        sig = base64.b64encode(hmac.new(key_bytes, c.encode(), hashlib.sha256).digest()).decode()
        if sig == expected_mac:
            print(f"🔥 MATCHED MAC FORMAT! Candidate: '{c}'")
            break
        else:
            print(f"Candidate '{c}' -> {sig} (expected {expected_mac})")
