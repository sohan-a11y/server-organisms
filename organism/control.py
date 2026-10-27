"""Control plane lite: signed heartbeat + signed update with canary rollback.
Update artifact is signed with HMAC(BROKER_TOKEN). Apply writes candidate,
runs a health callback on the candidate, and only then swaps it in; any
failure restores last-known-good atomically. Unsigned/bad updates never apply.
"""
import hashlib
import hmac
import json
import os
import time

def sign(secret, payload: bytes) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

def heartbeat(secret, version):
    body = {"ts": time.strftime("%H:%M:%S"), "version": version, "kind": "heartbeat"}
    body["sig"] = sign(secret, json.dumps({k: body[k] for k in ("ts", "version", "kind")}, sort_keys=True).encode())
    return body

def verify(secret, payload: bytes, sig) -> bool:
    return bool(secret) and hmac.compare_digest(sign(secret, payload), sig or "")

def apply_update(secret, manifest, current_path, health_fn):
    """manifest: {version, content, sig}. Returns (outcome, detail)."""
    payload = manifest.get("content", "").encode()
    if not verify(secret, payload, manifest.get("sig")):
        return "REJECTED-BAD-SIGNATURE", "signature mismatch; update never applied"
    candidate = current_path + ".candidate"
    backup = current_path + ".last-good"
    try:
        if os.path.exists(current_path):
            with open(current_path, "rb") as f:
                old = f.read()
            with open(backup, "wb") as f:
                f.write(old)
        with open(candidate, "wb") as f:
            f.write(payload)
        if not health_fn(candidate):
            _restore(current_path, backup)
            return "ROLLED-BACK", "candidate failed health check; last-known-good restored"
        os.replace(candidate, current_path)
        return "APPLIED", f"version {manifest.get('version')} live; previous kept at {backup}"
    except Exception as e:
        _restore(current_path, backup)
        return "ROLLED-BACK", f"apply error ({e}); last-known-good restored"

def _restore(path, backup):
    try:
        if os.path.exists(backup):
            os.replace(backup, path)
        elif os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
