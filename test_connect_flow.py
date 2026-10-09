import requests, json, time, websocket

phone = "7016648569"
fpath = f".session_{phone}.json"
cookies = json.load(open(fpath))

s = requests.Session()
cookie_dict = {}
for c in cookies:
    cookie_dict[c["name"]] = c["value"]

for k, v in cookie_dict.items():
    s.cookies.set(k, v)

s.headers.update({
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9,hi;q=0.8",
    "content-type": "application/json",
    "origin": "https://thunder-zone.coke2home.com",
    "referer": "https://thunder-zone.coke2home.com/game?skipWin=1",
    "sec-ch-ua": '"Chromium";v="154", "Google Chrome";v="154", "Not A(Brand";v="99"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": '"Android"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": "Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36",
    "x-botd": "human"
})

r_me = s.get("https://thunder-zone.coke2home.com/api/thunder-trail/me")
print("ME Status:", r_me.status_code, r_me.text)

r_sess = s.post("https://thunder-zone.coke2home.com/api/thunder-trail/sessions", json={})
print("Sessions Status:", r_sess.status_code, r_sess.text[:300])

if r_sess.status_code in (200, 201):
    sd = r_sess.json().get("data", {})
    sid = sd.get("session_id")
    ticket = sd.get("socket_ticket")
    frame_key = sd.get("frame_key")
    print(f"Got session_id: {sid}, ticket: {ticket[:20]}...")
    
    cookie_header = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])
    ws_headers = [
        "User-Agent: Mozilla/5.0 (Linux; Android 16; Pixel 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Mobile Safari/537.36",
        "Accept-Language: en-US,en;q=0.9,hi;q=0.8",
        f"Cookie: {cookie_header}"
    ]
    try:
        ws = websocket.create_connection(
            "wss://thunder-zone.coke2home.com/backend/api/v1/thunder-trails/ws",
            origin="https://thunder-zone.coke2home.com",
            header=ws_headers,
            timeout=5
        )
        print("WS CONNECT SUCCESS!")
        ws.close()
    except Exception as e:
        print("WS Connect Failed:", e)
