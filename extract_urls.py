import re

content = open("game_chunk.js", errors="ignore").read()
urls = set(re.findall(r'https?://[^\s"\'<>]+', content))
for u in sorted(urls):
    if any(k in u.lower() for k in ["gully", "redeem", "coke", "firefox", "reward", "claim", "shop"]):
        print(u)
