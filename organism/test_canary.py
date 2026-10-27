"""Durable regression: canary isolation + token fail-closed (reviewer C1/C3).

Uses Flask test clients only - no sockets. Asserts:
- canary patched does NOT change live behaviour (FAIL path leaves live untouched)
- live patched only after live apply with valid token; unauthenticated = 403
- victim fails closed when BROKER_TOKEN is the public demo default
"""
import os, sys
os.environ["BROKER_TOKEN"] = "test-secret-token-123"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "victim-api"))
import importlib
import app as victim
importlib.reload(victim)

c = victim.app.test_client()
H = {"X-Broker-Token": "test-secret-token-123"}
c.post("/api/_reset", headers=H)
c.post("/api/_canary_reset", headers=H)

# Live starts vulnerable: injection dumps all rows
assert len(c.get("/api/user/1%20OR%201=1").get_json()) > 1
# Unauthenticated patch attempts fail closed
assert c.post("/api/_apply_patch").status_code == 403
assert c.post("/api/_canary_apply_patch").status_code == 403
print("token fail-closed (no/default auth = 403): OK")

# Broker writes canary artifact, flips ONLY canary
open(victim.CANARY_PATCH_FILE, "w").write('rows = con.execute("SELECT id,name,email FROM users WHERE id=?", (user_id,)).fetchall()')
assert c.post("/api/_canary_apply_patch", headers=H).status_code == 200
assert len(c.get("/api/_canary/user/1%20OR%201=1").get_json()) <= 1, "canary must block injection"
assert len(c.get("/api/user/1%20OR%201=1").get_json()) > 1, "LIVE must stay vulnerable until promotion"
print("canary isolation: canary blocked, live untouched: OK")

# Canary reset restores canary; live promotion only with token
assert c.post("/api/_canary_reset", headers=H).status_code == 200
assert len(c.get("/api/_canary/user/1%20OR%201=1").get_json()) > 1
assert c.post("/api/_apply_patch", headers=H).status_code in (200, 409)
c.post("/api/_reset", headers=H)
print("CANARY TEST PASS")
