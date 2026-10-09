import json, re

har_path = "thunder-zone.coke2home.com.har"
try:
    with open(har_path, "r", encoding="utf-8", errors="ignore") as f:
        har_text = f.read()
        print("HAR loaded, searching for gullylabs / firefox redemption links...")
        matches = set(re.findall(r'https?://[^\s"\'<>]*gully[^\s"\'<>]*', har_text, re.I))
        for m in matches:
            print("Gully match:", m)
        
        matches_redeem = set(re.findall(r'https?://[^\s"\'<>]*redeem[^\s"\'<>]*', har_text, re.I))
        for m in matches_redeem:
            print("Redeem match:", m)

        matches_brands = set(re.findall(r'https?://(?:www\.)?[a-zA-Z0-9-]+\.(?:com|in|io|co)[^\s"\'<>]*', har_text))
        print("\nAll distinct domains in HAR:")
        domains = set(re.findall(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', har_text))
        for d in sorted(domains):
            if "coca" not in d and "google" not in d and "coke" not in d and "schema" not in d and "w3" not in d:
                print("External domain:", d)
except Exception as e:
    print("Error:", e)
