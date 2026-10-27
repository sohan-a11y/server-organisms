import subprocess
import sys
import time
import os
import secrets
import requests

os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["no_proxy"] = "127.0.0.1,localhost"
# Random per-run broker token (never the public demo default).
TOKEN = os.environ.get("BROKER_TOKEN") or secrets.token_hex(16)
os.environ["BROKER_TOKEN"] = TOKEN
HDR = {"X-Broker-Token": TOKEN}
env = dict(os.environ, VICTIM_URL="http://127.0.0.1:18001", BROKER_TOKEN=TOKEN)
procs = []
def start(cmd, e=None):
    p = subprocess.Popen([sys.executable] + cmd, env=e or env)
    procs.append(p); return p

def wait_health(url, timeout=20):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=2).ok:
                return True
        except Exception:
            pass
        time.sleep(0.3)
    raise AssertionError(f"not healthy: {url}")

try:
    start(["victim-api/app.py"])
    wait_health("http://127.0.0.1:18001/health")
    requests.post("http://127.0.0.1:18001/api/_reset", timeout=5, headers=HDR)
    start(["organism/broker.py"])
    wait_health("http://127.0.0.1:18002/health")
    requests.post("http://127.0.0.1:18002/reset", timeout=5, headers=HDR)
    assert requests.get("http://127.0.0.1:18001/health", timeout=5).json()["mode"] == "vulnerable", "victim not vulnerable"
    assert len(requests.get("http://127.0.0.1:18001/api/user/1%20OR%201=1", timeout=5).json()) > 1, "exploit failed"
    print("1 exploit leaks all user records: OK")
    r = requests.post("http://127.0.0.1:18002/simulate-exploit", timeout=5, headers=HDR).json()
    assert r["leaked"] is True, r
    print("2 organism senses damage:", r["phase"])
    # Unauthenticated broker call must be rejected
    assert requests.post("http://127.0.0.1:18002/heal", timeout=5).status_code == 403
    print("2b unauthenticated heal rejected 403: OK")
    h = requests.post("http://127.0.0.1:18002/heal", timeout=60, headers=HDR).json()
    assert h["verdict"]["verdict"] == "PASS", h
    assert h["replay"]["attack_blocked"] and h["replay"]["normal_ok"] and h["replay"]["applied"], h
    print("3 heal PASS (canary verified, then promoted), attack blocked, normal ok:", h["patch"]["summary"])
    assert len(requests.get("http://127.0.0.1:18001/api/user/1%20OR%201=1", timeout=5).json()) <= 1
    print("4 post-patch injection blocked (<=1 row): OK")
    assert requests.get("http://127.0.0.1:18001/api/_patch_state", timeout=5).json()["patched"] is True
    print("4b persisted patch artifact on shared volume: OK")
    k = requests.post("http://127.0.0.1:18002/kill", timeout=5, headers=HDR).json()
    assert k["lease_active"] is False
    assert requests.post("http://127.0.0.1:18002/heal", timeout=5, headers=HDR).status_code == 403
    print("5 kill switch blocks healing: OK")
    print("SMOKE PASS")
finally:
    for p in procs:
        p.terminate()
    for p in procs:
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()
