import re

with open(r'C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (2)\run_all_nabab.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''def load_live_proxies() -> list:
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
    return LIVE_PROXIES'''

pattern = re.compile(r'def load_live_proxies\(\) -> List\[str\]:.*?return LIVE_PROXIES', re.DOTALL)
content = pattern.sub(replacement, content)

with open(r'C:\Users\Himanshu Kumar\OneDrive\Desktop\New folder (2)\run_all_nabab.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Patched load_live_proxies successfully.')
