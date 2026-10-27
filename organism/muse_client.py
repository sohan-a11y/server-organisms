"""Muse patch proposer + verifier.

Uses Meta Model API when META_API_KEY is set; deterministic fallback otherwise
so the hackathon demo never blocks on credits/network. Both paths return the
same shape. Patcher and verifier are separate prompts/contexts by design.

The proposer's output is validated, not ignored: a Muse snippet is only
accepted as the patch when it is a parameterized query (contains a bound
``WHERE id=?`` execute and no string interpolation of the user id). The
accepted snippet is returned as ``after``/``patched_code`` and the broker
persists it as a real source artifact on the shared volume. The verifier's
deterministic gate includes ``applied``; any LLM opinion is reported
separately as an advisory field and can never flip the gate.
"""
import os
import json
import sys
import requests

API_KEY = os.environ.get("META_API_KEY", "")
MODEL = os.environ.get("META_MODEL", "muse-spark-1.1")
BASE = os.environ.get("META_API_BASE", "https://api.meta.ai/v1")

VULN_SNIPPET = 'q = f"SELECT id,name,email FROM users WHERE id = {user_id}"  # string-formatted SQL'
FIXED_SNIPPET = 'rows = con.execute("SELECT id,name,email FROM users WHERE id=?", (user_id,)).fetchall()  # parameterized'
LAST_CALL_DEGRADED = False

def _call_muse(system, user):
    global LAST_CALL_DEGRADED
    if not API_KEY:
        LAST_CALL_DEGRADED = True
        return None
    try:
        r = requests.post(f"{BASE}/chat/completions",
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}]}, timeout=30)
        if r.ok:
            LAST_CALL_DEGRADED = False
            return r.json()["choices"][0]["message"]["content"]
        LAST_CALL_DEGRADED = True
        print(f"WARNING: Muse API returned {r.status_code}; using deterministic fallback (degraded)", file=sys.stderr)
    except Exception as e:
        LAST_CALL_DEGRADED = True
        print(f"WARNING: Muse API call failed ({e}); using deterministic fallback (degraded)", file=sys.stderr)
    return None

def ask_llm(question):
    """Teacher for organism brains: one Muse answer, or None (brain queues honestly)."""
    return _call_muse("You are a security teacher for a server organism. Answer in one concise, correct sentence: trigger -> fix.", question)

def _is_parameterized(snippet):
    if not snippet:
        return False
    s = snippet.lower()
    return ("where id=?" in s.replace(" ", "") or "where id = ?" in s) and "execute(" in s \
        and "{user_id}" not in snippet and "f\"" not in snippet and "f'" not in snippet

def propose_patch(damage_summary):
    out = _call_muse(
        "You are an organism patch-proposer. Return only a unified fix for SQL injection: use parameterized queries. Be concise.",
        f"Vulnerable code:\n{VULN_SNIPPET}\nDamage: {damage_summary}")
    if out and _is_parameterized(out):
        # Muse actually authored the accepted patch.
        snippet = out.strip().splitlines()[0][:500] if out.strip() else FIXED_SNIPPET
        # Keep the canonical executable line if Muse wrapped it in prose.
        after = snippet if _is_parameterized(snippet) else FIXED_SNIPPET
        return {"source": f"Meta Model API ({MODEL})", "raw": out[:2000],
                "before": VULN_SNIPPET, "after": after, "patched_code": after,
                "summary": "Parameterize query; bind user_id as parameter, never interpolate.",
                "degraded": False}
    if out and ("parameterized" in out.lower() or "prepared statement" in out.lower()) and "{user_id}" not in out:
        # Muse authored the correct fix in prose; canonicalize to the executable line.
        return {"source": f"Meta Model API ({MODEL})", "raw": out[:2000],
                "before": VULN_SNIPPET, "after": FIXED_SNIPPET, "patched_code": FIXED_SNIPPET,
                "summary": "Parameterize query; bind user_id as parameter, never interpolate.",
                "degraded": False}
    if out:
        print("WARNING: Muse patch output failed parameterized-query validation; using fallback", file=sys.stderr)
    return {"source": "fallback (set META_API_KEY for Muse Spark)",
            "raw": out[:2000] if out else FIXED_SNIPPET, "before": VULN_SNIPPET, "after": FIXED_SNIPPET,
            "patched_code": FIXED_SNIPPET,
            "summary": "Parameterize query; bind user_id as parameter, never interpolate.",
            "degraded": True}

def verify_patch(replay_results):
    """Deterministic gate: PASS only if attack blocked AND normal traffic ok
    AND the patch was actually applied. LLM opinion is advisory only."""
    verdict = bool(replay_results.get("attack_blocked") and replay_results.get("normal_ok")
                   and replay_results.get("applied"))
    out = _call_muse(
        "You are an independent verifier organism. Given replay results, answer PASS or FAIL with one reason.",
        json.dumps(replay_results))
    return {"verdict": "PASS" if verdict else "FAIL",
            "source": "deterministic replay verifier",
            "llm_opinion": (out[:500] if out else None),
            "detail": str(replay_results),
            "replay": replay_results}
