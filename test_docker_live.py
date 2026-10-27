import os, requests
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
tok = ""
for line in open(".env", encoding="utf-8"):
    if line.startswith("BROKER_TOKEN="):
        tok = line.strip().split("=", 1)[1]
H = {"X-Broker-Token": tok}
B = "http://127.0.0.1:18002"
for cls in ("auth", "xss"):
    r = requests.post(f"{B}/heal-class", headers=H, json={"class": cls}, timeout=30).json()
    assert r["verdict"]["verdict"] == "PASS" and r["promoted"], (cls, r)
    print(cls, "heal PASS promoted: OK")
a = requests.post(f"{B}/ask", headers=H, json={"question": "what stops sql injection?"}, timeout=30).json()
assert a["answer"]["known"], a
print("ask organism:", a["answer"]["answer"][:60], "| neurons", a["brain"]["neurons"])
requests.post(f"{B}/reset", headers=H, timeout=10)
print("DOCKER LIVE TEST PASS")
