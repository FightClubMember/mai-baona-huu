import json, sys, time
from live_websocket_runner import play_websocket_game

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception: pass

phone = sys.argv[1] if len(sys.argv) > 1 else "7726894595"
target = int(sys.argv[2]) if len(sys.argv) > 2 else 2680

print(f"\n========================================================")
print(f"🔥 CONSECUTIVE TOP 20 PUSH ON: {phone} | TARGET: {target} PTS")
print(f"========================================================\n")

for attempt in range(1, 6):
    print(f"\n>>> [ATTEMPT #{attempt}/5 ON {phone}] Starting Live Game...")
    try:
        success = play_websocket_game(phone, target_score=target)
        print(f">>> [ATTEMPT #{attempt}/5] Completed.")
    except Exception as e:
        print(f">>> [ATTEMPT #{attempt}/5] Error: {e}")
    
    time.sleep(3.0)

print(f"\n========================================================")
print(f"🏁 ALL ATTEMPTS COMPLETED FOR {phone}")
print(f"========================================================\n")
