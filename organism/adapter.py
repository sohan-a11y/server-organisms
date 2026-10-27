"""Per-app adapter: protect YOUR app without forking the organism.

Your app provides (config JSON): health URL, canary + live exploit-check URLs,
normal-traffic URLs, and a patch webhook that receives the verified artifact
with your token. The organism probes, canary-verifies, and only then calls
your webhook to promote. See adapter.example.json + ADAPTER.md.
"""
import requests

class AppAdapter:
    def __init__(self, cfg):
        self.cfg = cfg
        self.base = cfg["base_url"].rstrip("/")
        self.token = cfg.get("patch_token", "")

    def _get(self, path):
        try:
            return requests.get(self.base + path, timeout=5)
        except Exception:
            return None

    def probe_vulnerable(self, check):
        r = self._get(check["path"])
        if r is None:
            return False
        return check.get("marker", "") in r.text if "marker" in check else r.status_code == check.get("status", 200)

    def run(self, patch_artifact):
        c = self.cfg
        live_vuln = self.probe_vulnerable(c["live_check"])
        # canary verification against your canary twin
        canary_blocked = not self.probe_vulnerable(c["canary_check"])
        normal = self._get(c["normal_path"])
        normal_ok = bool(normal and normal.status_code == 200)
        replay = {"attack_blocked": canary_blocked, "normal_ok": normal_ok,
                  "applied": True, "live_was_vulnerable": live_vuln}
        promoted = False
        if canary_blocked and normal_ok:
            try:
                r = requests.post(self.base + c["patch_webhook"],
                                  json={"artifact": patch_artifact, "class": c.get("class", "custom")},
                                  headers={"X-Broker-Token": self.token}, timeout=10)
                promoted = bool(r.ok)
            except Exception:
                promoted = False
        return {"replay": replay, "promoted": promoted, "verdict": "PASS" if (canary_blocked and normal_ok and promoted) else "FAIL"}
