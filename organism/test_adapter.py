import os, sys
os.environ["BROKER_TOKEN"] = "test-secret-token-123"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "victim-api"))
sys.path.insert(0, ".")
import app as victim
from adapter import AppAdapter

# Serve victim via test client through a tiny requests shim is complex; instead
# assert adapter logic against live logic by monkeypatching _get/post is skipped.
# Here we verify config contract + probe semantics with a fake transport.
class FakeResp:
    def __init__(self, text, status=200):
        self.text, self.status_code = text, status
    @property
    def ok(self):
        return self.status_code < 400

cfg = {"base_url": "http://app", "patch_token": "t",
       "live_check": {"path": "/live", "marker": "VULN"},
       "canary_check": {"path": "/canary", "marker": "VULN"},
       "normal_path": "/ok", "patch_webhook": "/patch"}
a = AppAdapter(cfg)
a._get = lambda path: FakeResp("VULN" if path == "/live" else "hello") if "canary" not in path else FakeResp("safe")
import adapter as amod
orig_post = amod.requests.post
amod.requests.post = lambda url, json=None, headers=None, timeout=10: FakeResp("ok")
try:
    out = a.run("artifact-code")
    assert out["replay"]["live_was_vulnerable"] and out["replay"]["attack_blocked"], out
finally:
    amod.requests.post = orig_post
print("adapter contract (live vuln, canary blocked, promote): OK", out["verdict"])
print("ADAPTER TEST PASS")
