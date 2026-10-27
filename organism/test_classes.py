import os, sys
os.environ["BROKER_TOKEN"] = "test-secret-token-123"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "victim-api"))
import app as victim

c = victim.app.test_client()
H = {"X-Broker-Token": "test-secret-token-123"}
c.post("/api/_reset", headers=H)

# Broken auth: user 1 reads user 2 secret (vulnerable), canary fix blocks, live untouched until promote
assert c.get("/api/profile/2?as_user=1").status_code == 200
open(victim.CANARY_PATCH_FILE + ".auth", "w").write("check ownership on server  # check ownership")
assert c.get("/api/_canary/profile/2?as_user=1").status_code == 403
assert c.get("/api/profile/2?as_user=1").status_code == 200, "live must stay vulnerable pre-promotion"
print("broken-auth canary isolation: OK")

# XSS: script reflected (vulnerable), canary escaped, live untouched
assert "<script>alert" in c.get("/api/comment?name=<script>alert(1)</script>").text
open(victim.CANARY_PATCH_FILE + ".xss", "w").write("escape output as text  # escape output")
assert "<script>alert" not in c.get("/api/_canary/comment?name=<script>alert(1)</script>").text
assert "<script>alert" in c.get("/api/comment?name=<script>alert(1)</script>").text
print("xss canary isolation: OK")
c.post("/api/_reset", headers=H)
print("CLASSES TEST PASS")
