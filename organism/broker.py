"""Host broker: the Durgapala. Tiny privileged layer outside the organism brain.
Holds lease/kill-switch, containment, patch apply. Organism (NCA+Muse) proposes;
broker applies the patch to an isolated CANARY first, replays an exploit
corpus there, and only on PASS promotes the persisted patch artifact to the
live victim. FAIL (or a kill during the cycle) leaves the live victim
untouched.
"""
import os
import sys
import time
import base64
import threading
import requests
from flask import Flask, jsonify, request
from nca import NCAGrid
import muse_client
from agents import Orchestrator, guna_of
orch = Orchestrator()
from life import Population
pop = Population()
try:
    import json as _json
    from life import Genome as _Genome
    _tg = _json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trained_genome.json")))
    _g = _tg["genome"]
    for _o in pop.members:
        _o.genome = _Genome(_g["heal_rate"], _g["harm_rate"], _g["signal_decay"])
except Exception:
    pass
from brain import Brain
brain = Brain("swarm-leader", llm_ask=muse_client.ask_llm)
peers = [Brain(f"org-peer-{i}", llm_ask=None) for i in range(3)]

# --- Persistence: brain + population survive restart via shared volume ---
import json as _state_json
STATE_FILE = os.environ.get("ORGANISM_STATE_FILE", "/tmp/organism_state.json")
_save_counter = [0]
def _save_state():
    try:
        d = os.path.dirname(STATE_FILE)
        if d:
            os.makedirs(d, exist_ok=True)
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w") as f:
            _state_json.dump({"brain": brain.export_state(), "life": pop.export_state()}, f)
        os.replace(tmp, STATE_FILE)
    except Exception:
        pass
def _load_state():
    try:
        with open(STATE_FILE) as f:
            data = _state_json.load(f)
        brain.import_state(data.get("brain")); pop.import_state(data.get("life"))
        pkt = brain.teach_packet()
        for p in peers:
            p.receive_teaching(pkt)
    except Exception:
        pass
_load_state()

app = Flask(__name__)

@app.after_request
def cors(r):
    # Dashboard is served from the dashboard origin on the same host; do not
    # allow arbitrary sites to drive the control plane.
    origin = request.headers.get("Origin", "")
    allowed = {"http://127.0.0.1:18000", "http://localhost:18000"}
    if origin in allowed:
        r.headers["Access-Control-Allow-Origin"] = origin
    r.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Broker-Token"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return r

VICTIM = os.environ.get("VICTIM_URL", "http://127.0.0.1:18001")
LOG = os.environ.get("SHARED_LOG", "/shared/access.log")
TOKEN = os.environ.get("BROKER_TOKEN", "")
_TOKEN_SECURE = bool(TOKEN) and TOKEN != "demo-broker-token"
if not _TOKEN_SECURE:
    print("WARNING: BROKER_TOKEN is unset or is the public demo default. "
          "Mutating broker routes and victim patch endpoints fail closed (403). "
          "Set BROKER_TOKEN to a random secret (see .env.example).", file=sys.stderr)

# Persisted patch artifacts on the shared volume (survive victim restart).
_HERE = os.path.dirname(os.path.abspath(__file__))
_SHARED_DEFAULT = os.path.join(_HERE, "..", "shared-patch", "patched_app.py")
PATCH_FILE = os.environ.get("PATCH_FILE", _SHARED_DEFAULT)
CANARY_PATCH_FILE = os.environ.get("CANARY_PATCH_FILE", PATCH_FILE + ".canary")

grid = NCAGrid()
state = {"phase": "healthy", "lease_active": True, "contained": False,
         "patched": False, "last_patch": None, "last_verdict": None,
         "agent_trail": [], "lease_epoch": 0}
swarm_log = []
_lock = threading.RLock()

def _require_auth():
    """Mutating broker routes require the operator/broker token. Fails
    closed when no secure token is configured."""
    if not _TOKEN_SECURE:
        return jsonify(error="broker token not configured: set BROKER_TOKEN to a random secret"), 403
    if request.headers.get("X-Broker-Token") != TOKEN:
        return jsonify(error="forbidden: broker token required"), 403
    return None

def swarm_say(sender, intent):
    # Swarm log encoding (XOR+base64) for compact display only. This is
    # obfuscation, NOT encryption: no secrecy claim is made anywhere.
    key = b"organism-swarm-key"
    raw = intent.encode()
    ct = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
    with _lock:
        swarm_log.append({"from": sender, "ciphertext": base64.b64encode(ct).decode()[:64],
                          "intent": intent, "ts": time.strftime("%H:%M:%S")})
        del swarm_log[:-30]

def victim(path, method="GET", auth=False, **kw):
    if auth or path.startswith("/api/_"):
        kw.setdefault("headers", {})["X-Broker-Token"] = TOKEN
    try:
        return requests.request(method, f"{VICTIM}{path}", timeout=5, **kw)
    except Exception:
        return None

# Exploit replay corpus: the whole injection class, not one payload.
PAYLOADS = ["1 OR 1=1", "1' OR '1'='1", "1 OR 1=1 --", "1 UNION SELECT id,name,email FROM users"]

def _rows(path):
    r = victim(path)
    if r is None:
        return None
    try:
        data = r.json()
        return data if isinstance(data, list) else None
    except Exception:
        return None

def exploit_succeeds(prefix=""):
    rows = _rows(f"{prefix}/api/user/1%20OR%201=1") if not prefix else _rows(f"{prefix}1%20OR%201=1")
    return bool(rows and len(rows) > 1)

def _replay_on(base_user_path, applied):
    """Replay the full payload corpus + normal traffic against one target.
    base_user_path e.g. '/api/user/' (live) or '/api/_canary/user/'."""
    blocked = True
    details = {}
    for p in PAYLOADS:
        enc = p.replace(" ", "%20").replace("'", "%27")
        rows = _rows(f"{base_user_path}{enc}")
        ok = rows is not None and len(rows) <= 1
        details[p] = ok
        blocked = blocked and ok
    n1 = _rows(f"{base_user_path}1")
    n2 = _rows(f"{base_user_path}2")
    normal_ok = bool(n1 and len(n1) == 1 and n2 and len(n2) == 1)
    return {"attack_blocked": blocked, "normal_ok": normal_ok,
            "applied": bool(applied), "payloads": details}

def _write_patch_artifact(path, patch):
    """Persist the validated patched source as a real artifact (atomic)."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    code = patch.get("patched_code") or patch.get("after") or muse_client.FIXED_SNIPPET
    content = ("# Patched source artifact written by host broker (canary-verified before promotion).\n"
               "# Vulnerable: " + muse_client.VULN_SNIPPET + "\n"
               + code + "\n")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(content)
    os.replace(tmp, path)
    return content

def _remove(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def tick():
    while True:
        time.sleep(0.6)
        with _lock:
            if state["lease_active"]:
                grid.step(genome=pop.leader_genome()); pop.tick()
                _save_counter[0] += 1
                if _save_counter[0] % 20 == 0:
                    _save_state()

threading.Thread(target=tick, daemon=True).start()

# --- Autonomous sensing: probe for live exploitation without any button ---
MODE = os.environ.get("ORGANISM_MODE", "suggest")  # suggest = human approves heal; auto = heal on detection
_last_auto_heal = [0.0]
def _watcher():
    time.sleep(4)
    while True:
        time.sleep(5)
        try:
            with _lock:
                if not state["lease_active"] or state["phase"] in ("patching", "killed"):
                    continue
                phase = state["phase"]
            if phase == "healed":
                continue
            leaked = exploit_succeeds()
            if leaked:
                with _lock:
                    grid.exploit(1.0)
                    if state["phase"] == "healthy":
                        state["phase"] = "under-attack"
                    state["pending_attack"] = True
                swarm_say("sensor", "autonomous probe: live exploit detected, awaiting approval" if MODE != "auto" else "autonomous probe: healing now (auto mode)")
                if MODE == "auto" and time.time() - _last_auto_heal[0] > 30:
                    _last_auto_heal[0] = time.time()
                    try:
                        requests.post("http://127.0.0.1:18002/heal", headers={"X-Broker-Token": TOKEN}, timeout=60)
                    except Exception:
                        pass
        except Exception:
            pass
threading.Thread(target=_watcher, daemon=True).start()

@app.get("/state")
def get_state():
    with _lock:
        snap = grid.snapshot()
        # Source of truth for patched is the victim, not local memory.
        ps = victim("/api/_patch_state")
        patched_live = state["patched"]
        if ps is not None and ps.ok:
            try:
                patched_live = bool(ps.json().get("patched"))
                state["patched"] = patched_live
            except Exception:
                pass
        return jsonify(phase=state["phase"], lease_active=state["lease_active"],
                       contained=state["contained"], patched=patched_live,
                       last_patch=state["last_patch"], last_verdict=state["last_verdict"],
                       grid=snap, swarm=swarm_log[-12:],
                       guna=guna_of(state["phase"], snap["alive_cells"] / max(1, snap["total"])),
                       agent_trail=state.get("agent_trail", []), life=pop.snapshot(),
                       mode=MODE, pending_attack=state.get("pending_attack", False),
                       brain=brain.snapshot(), peers=[p.snapshot() for p in peers])

@app.post("/simulate-exploit")
def simulate_exploit():
    denied = _require_auth()
    if denied:
        return denied
    with _lock:
        if not state["lease_active"]:
            return jsonify(error="organisms dead: lease withdrawn"), 403
        epoch = state["lease_epoch"]
    leaked = exploit_succeeds()
    with _lock:
        if state["lease_epoch"] != epoch or not state["lease_active"]:
            return jsonify(error="kill switch active: aborted"), 403
        grid.exploit(1.0 if leaked else 0.5)
        state["phase"] = "under-attack" if leaked else "probing"
    swarm_say("cell-8,8", "damage sensed at /api/user - neighbours converge")
    swarm_say("broker", "containing: endpoint flagged, patch requested from Muse")
    return jsonify(leaked=leaked, phase=state["phase"])

@app.post("/heal")
def heal():
    denied = _require_auth()
    if denied:
        return denied
    with _lock:
        if not state["lease_active"]:
            return jsonify(error="kill switch active: cannot patch"), 403
        state["phase"] = "patching"; state["contained"] = True
        epoch = state["lease_epoch"]
    patch = muse_client.propose_patch("SQL injection on /api/user/<id>: injection dumps all user records (id/name/email)")

    def _preflight():
        h = victim("/health")
        return bool(h and h.ok)

    def _apply_canary():
        # Write canary artifact first, then flip ONLY the canary.
        _write_patch_artifact(CANARY_PATCH_FILE, patch)
        r = victim("/api/_canary_apply_patch", method="POST", auth=True)
        return bool(r and r.ok)

    def _replay_canary(applied):
        return _replay_on("/api/_canary/user/", applied)

    def _rollback_canary():
        victim("/api/_canary_reset", method="POST", auth=True)
        _remove(CANARY_PATCH_FILE)

    swarm_say("muse-proposer", patch["summary"])
    cycle = orch.run_heal_cycle(observed="exploit replay leaked all user records", severity="leak",
                                confidence=0.95, patch=patch, apply_fn=_apply_canary,
                                replay_fn=_replay_canary, rollback_fn=_rollback_canary,
                                preflight_fn=_preflight)
    # Single replay/verify gate: the orchestrator's canary result. No second pass.
    replay = cycle.get("replay") or {"attack_blocked": False, "normal_ok": False, "applied": False}
    verdict = muse_client.verify_patch(replay)
    verdict["agent_cycle"] = cycle["outcome"]
    healed = cycle["outcome"] == "HEALED" and verdict["verdict"] == "PASS"

    if healed:
        # Re-check the kill switch immediately before promotion (TOCTOU fix).
        with _lock:
            if state["lease_epoch"] != epoch or not state["lease_active"]:
                _rollback_canary()
                state["phase"] = "killed"
                return jsonify(error="kill switch active: promotion aborted, live untouched"), 403
        # Promote: persist the same artifact to the live patch file, then flip live.
        _write_patch_artifact(PATCH_FILE, patch)
        r = victim("/api/_apply_patch", method="POST", auth=True)
        if not (r and r.ok):
            _rollback_canary()
            with _lock:
                state["phase"] = "patch-rejected"; state["agent_trail"] = cycle.get("trail", [])
                state["last_patch"] = patch; state["last_verdict"] = verdict
            return jsonify(patch=patch, verdict={"verdict": "FAIL", "detail": "live promotion refused by victim"},
                           replay=replay), 502
        _rollback_canary()
    else:
        _rollback_canary()

    with _lock:
        state["agent_trail"] = cycle.get("trail", [])
        if healed:
            state["patched"] = True; state["phase"] = "healed"; grid.heal_all()
            pop.record_outcome(True)
            brain.reward("sql injection", True)
            pkt = brain.teach_packet()
            for p in peers:
                p.receive_teaching(pkt)
            swarm_say("brain", f"heal learned; taught {len(peers)} peers, neurons={brain.snapshot()['neurons']}")
        else:
            # FAIL leaves the live victim untouched (canary already reset).
            state["phase"] = "patch-rejected"
            pop.record_outcome(False)
        state["last_patch"] = patch; state["last_verdict"] = verdict
    swarm_say("verifier", f"canary replay verdict {verdict['verdict']}: attack_blocked={replay['attack_blocked']}")
    return jsonify(patch=patch, verdict=verdict, replay=replay)


CLASS_FIX = {
    "auth": ("check ownership on server for every record access; return 403 when as_user != id  # check ownership",
             "broken authorization lets user read another user record by changing id"),
    "xss": ("escape output and set content security policy; render name as text  # escape output",
            "reflected xss script executes in victim browser when name is rendered"),
}

@app.post("/heal-class")
def heal_class():
    denied = _require_auth()
    if denied:
        return denied
    cls = (request.get_json(silent=True) or {}).get("class", "")
    if cls not in CLASS_FIX:
        return jsonify(error="unknown class; use sql via /heal or auth/xss here"), 400
    with _lock:
        if not state["lease_active"]:
            return jsonify(error="kill switch active"), 403
    code, trigger = CLASS_FIX[cls]
    canary_file = CANARY_PATCH_FILE + (".auth" if cls == "auth" else ".xss")
    _write_patch_artifact(canary_file, {"patched_code": code, "after": code})
    # verify on canary twins
    if cls == "auth":
        bad = victim("/api/_canary/profile/2?as_user=1")
        good = victim("/api/profile/1?as_user=1")
        canary_blocked = bad is not None and bad.status_code == 403
        normal_ok = bool(good and good.status_code == 200)
        live_before = victim("/api/profile/2?as_user=1")
        live_vuln = bool(live_before and live_before.status_code == 200)
    else:
        payload = "<script>alert(1)</script>"
        cr = victim(f"/api/_canary/comment?name={payload}")
        canary_blocked = bool(cr and "<script>alert" not in cr.text)
        normal_ok = bool(cr and "hello" in cr.text)
        live_before = victim(f"/api/comment?name={payload}")
        live_vuln = bool(live_before and "<script>alert" in live_before.text)
    replay = {"attack_blocked": canary_blocked, "normal_ok": normal_ok, "applied": True, "live_was_vulnerable": live_vuln}
    verdict = muse_client.verify_patch(replay)
    promoted = False
    if verdict["verdict"] == "PASS":
        r = victim("/api/_apply_class_patch", method="POST", auth=True, json={"class": cls})
        promoted = bool(r and r.ok)
        brain.learn(trigger, code, source="heal-class", confidence=0.6)
        brain.reward(trigger, True)
        pkt = brain.teach_packet()
        for peer in peers:
            peer.receive_teaching(pkt)
    return jsonify(**{"class": cls, "verdict": verdict, "replay": replay, "promoted": promoted})

@app.post("/kill")
def kill():
    denied = _require_auth()
    if denied:
        return denied
    with _lock:
        state["lease_active"] = False; state["lease_epoch"] += 1
        grid.alive = False; state["phase"] = "killed"
    swarm_say("control-plane", "LEASE WITHDRAWN - all organisms halt (kill switch)")
    return jsonify(lease_active=False, phase="killed")

@app.post("/revive")
def revive():
    denied = _require_auth()
    if denied:
        return denied
    with _lock:
        state["lease_active"] = True; state["lease_epoch"] += 1
        grid.alive = True; state["phase"] = "healthy"
    return jsonify(lease_active=True)

@app.post("/reset")
def reset():
    denied = _require_auth()
    if denied:
        return denied
    victim("/api/_reset", method="POST", auth=True)
    _remove(PATCH_FILE); _remove(CANARY_PATCH_FILE)
    with _lock:
        grid.reset(); state.update(phase="healthy", contained=False, patched=False,
                                   last_patch=None, last_verdict=None, agent_trail=[], pending_attack=False)
        swarm_log.clear()
    return jsonify(ok=True)

@app.post("/ask")
def ask_organism():
    denied = _require_auth()
    if denied:
        return denied
    q = ((request.get_json(silent=True) or {}).get("question", "") or "").strip()
    if not q:
        return jsonify(error="question required"), 400
    with _lock:
        if not state["lease_active"]:
            return jsonify(error="organisms dead: lease withdrawn"), 403
        # Guard brain under the same lock as tick/state (no lock-free mutation).
        # NOTE: no swarm teaching here - only verified heals teach peers.
        ans = brain.ask(q)
        snap = brain.snapshot()
    return jsonify(answer=ans, brain=snap)

@app.get("/health")
def health():
    return jsonify(status="ok", lease_active=state["lease_active"])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=18002)
