import requests
import concurrent.futures

PROXY_SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt"
]

def check_proxy(proxy):
    try:
        r = requests.get("https://thunder-zone.coke2home.com", proxies={"http": proxy, "https": proxy}, timeout=3)
        if r.status_code == 200:
            return proxy
    except Exception:
        pass
    return None

def main():
    print("Downloading proxies...")
    proxies = set()
    for src in PROXY_SOURCES:
        try:
            r = requests.get(src, timeout=5)
            if r.status_code == 200:
                lines = [line.strip() for line in r.text.splitlines() if ":" in line]
                proxies.update([f"http://{p}" if not p.startswith("http") else p for p in lines[:200]])
        except Exception:
            pass
            
    proxy_list = list(proxies)
    print(f"Downloaded {len(proxy_list)} proxies. Testing them concurrently...")
    
    valid_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_proxy, proxy_list)
        for res in results:
            if res:
                valid_proxies.append(res)
                
    print(f"Found {len(valid_proxies)} working proxies.")
    with open("valid_proxies.txt", "w") as f:
        for p in valid_proxies:
            f.write(p + "\n")

if __name__ == "__main__":
    main()
