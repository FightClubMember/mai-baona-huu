import json, os, sys, base64, hmac, hashlib

# Signing function extracted from game engine:
# message format: `${session_id}|${seq}|${ts}|${t}|${payload_fields}`
# hello: `${ticket}|${resume_from_seq||0}`
# ready: ``
# swipe: `${box_id}|${dir}|${client_at_ms}`
# pong:  `${nonce}`

session_id = "9fdee2b8-09f4-4d70-84f3-a794f49aecfb"
frame_key = "hAbPxwehlp9dcNbJA43gW923+ZXd8o8K9hm5phZlD+w="
key_bytes = base64.b64decode(frame_key)

def sign_msg(t, seq, ts, p):
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
    return sig, raw_str

# Test on hello message from HAR:
# send: {"v":1,"t":"hello","seq":1,"ts":435,"p":{"session_id":"9fdee2b8-09f4-4d70-84f3-a794f49aecfb","ticket":"esZu38kIGinO-QuguwsyVA.1791461182188.Xdx647ec7n5os1OK4bk0GmHGHvu8DaD1Zdo1E7zCYL4"},"mac":"Nw9ZONO3BqSe72z19WDXr7/rK1YppvycpPaq060NzLA="}

ticket = "esZu38kIGinO-QuguwsyVA.1791461182188.Xdx647ec7n5os1OK4bk0GmHGHvu8DaD1Zdo1E7zCYL4"
hello_p = {"session_id": session_id, "ticket": ticket}
sig, raw = sign_msg("hello", 1, 435, hello_p)

print(f"Raw string: '{raw}'")
print(f"Computed MAC: {sig}")
print(f"Expected MAC: Nw9ZONO3BqSe72z19WDXr7/rK1YppvycpPaq060NzLA=")
print(f"MATCH: {sig == 'Nw9ZONO3BqSe72z19WDXr7/rK1YppvycpPaq060NzLA='}")

# Test on ready:
# send: {"v":1,"t":"ready","seq":2,"ts":436,"p":{},"mac":"aN7iJjrIktMDdZTyFodO8j4b5gKZ21FA3cqkE7VUyEE="}
sig_ready, raw_ready = sign_msg("ready", 2, 436, {})
print(f"\nReady match: {sig_ready == 'aN7iJjrIktMDdZTyFodO8j4b5gKZ21FA3cqkE7VUyEE='}")

# Test on swipe:
# send: {"v":1,"t":"swipe","seq":4,"ts":1558,"p":{"box_id":1,"dir":"right","client_at_ms":1558},"mac":"P4edSsr0b6P520XYC4jGKh48rmOIvGQryL36Bmh4LlI="}
sig_swipe, raw_swipe = sign_msg("swipe", 4, 1558, {"box_id":1,"dir":"right","client_at_ms":1558})
print(f"\nSwipe match: {sig_swipe == 'P4edSsr0b6P520XYC4jGKh48rmOIvGQryL36Bmh4LlI='}")
