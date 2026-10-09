import requests, re

url = "https://thunder-zone.coke2home.com/game"
headers = {"User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/124.0.0.0 Mobile Safari/537.36"}

r = requests.get(url, headers=headers)
print("Game status:", r.status_code)

scripts = re.findall(r'src=["\']([^"\']+)["\']', r.text)
for s in scripts:
    print("Found script:", s)
