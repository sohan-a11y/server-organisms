import os
import time
import requests
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
tok = ""
for line in open(".env", encoding="utf-8"):
    if line.startswith("BROKER_TOKEN="):
        tok = line.strip().split("=", 1)[1]
H = {"X-Broker-Token": tok}
B, V = "http://127.0.0.1:18002", "http://127.0.0.1:18001"

def post(path, **kw):
    return requests.post(B + path, headers=H, timeout=60, **kw)

post("/reset")
# 1. Autonomous sensing: NO simulate-exploit call. Watcher must detect within ~15s.
deadline = time.time() + 20
phase = ""
while time.time() < deadline:
    s = requests.get(B + "/state", timeout=5).json()
    phase = s["phase"]
    if s.get("pending_attack") and phase == "under-attack":
        break
    time.sleep(2)
assert s.get("pending_attack") and phase == "under-attack", s.get("phase")
print("1 autonomous sensing (no button): phase under-attack, pending_attack True: OK, mode", s.get("mode"))

# 2. Ask unknown-ish, heal all classes
a = post("/ask", json={"question": "what stops sql injection dumps?"})
print("2 ask before heal known:", a.json()["answer"]["known"])
assert post("/heal").json()["verdict"]["verdict"] == "PASS"
for cls in ("auth", "xss"):
    r = post("/heal-class", json={"class": cls}).json()
    assert r["verdict"]["verdict"] == "PASS" and r["promoted"], (cls, r)
print("2 heal sql+auth+xss PASS in Docker: OK")

# 3. Learn something, capture neurons, restart organism, must remember
post("/ask", json={"question": "how to stop timing side channel in token compare?"})
before = requests.get(B + "/state", timeout=5).json()["brain"]["neurons"]
print("3 neurons before restart:", before)
os.system("docker compose restart organism")
time.sleep(8)
after_state = requests.get(B + "/state", timeout=10).json()
after = after_state["brain"]["neurons"]
assert after >= before - 2, (before, after)
print(f"3 persistence across organism restart: neurons {before} -> {after}, population {after_state['life']['population']}: OK")
post("/reset")
print("DOCKER GOAL TEST PASS")
