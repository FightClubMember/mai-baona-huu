import re

content = open("game_chunk.js", errors="ignore").read()
print("--- ALL DOMAINS / WEBSITES IN JS ---")
domains = set(re.findall(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content))
for d in sorted(domains):
    print(d)

print("\n--- BRAND / REDEEM TEXT CONTEXT ---")
lines = content.split('\n')
for line in lines:
    if any(k in line.lower() for k in ["gullylabs", "gully labs", "gully", "firefox", "redemption", "voucher"]):
        print(line[:200])
