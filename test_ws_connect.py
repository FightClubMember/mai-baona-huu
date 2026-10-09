import requests, websocket, json, time, os, threading

# We have socket_ticket & frame_key
ticket = "vkIAWG_RXvxacGgenBsfFQ.1791458955117._7olxgH6R3UiZyp0N_hDgMOhtBXatslAOSj4ymIk-D0"
sid = "3e01db78-4749-4827-ba9f-fc6906d75fe0"

# Common WebSocket endpoints for this backend
possible_ws_urls = [
    f"wss://thunder-zone.coke2home.com/ws?ticket={ticket}",
    f"wss://thunder-zone.coke2home.com/ws/game?ticket={ticket}",
    f"wss://thunder-zone.coke2home.com/socket.io/?EIO=4&transport=websocket&ticket={ticket}",
    f"wss://thunder-zone.coke2home.com/game/ws?ticket={ticket}",
    f"wss://thunder-zone.coke2home.com/api/ws?ticket={ticket}",
    f"wss://thunder-zone.coke2home.com/api/thunder-trail/ws?ticket={ticket}"
]

for url in possible_ws_urls:
    print(f"Testing WebSocket connection to: {url}")
    try:
        ws = websocket.create_connection(url, timeout=3, header=["Origin: https://thunder-zone.coke2home.com"])
        print(f"🔥 SUCCESS CONNECTED to {url}!")
        ws.send(json.dumps({"type": "init", "session_id": sid, "ticket": ticket}))
        resp = ws.recv()
        print(f"Received from WS: {resp}")
        ws.close()
        break
    except Exception as e:
        print(f"Failed ({url}): {e}")
