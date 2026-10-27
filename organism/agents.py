"""Agent roster structured from Indian knowledge systems.

Design (search-first synthesis):
- Deterministic orchestrator owns state/budgets/gates. Agents never 'agree' to pass;
  only pre-registered evidence gates pass (Nyaya Pramana).
- Prashnika (Purva Paksha) always questions. Margadarshi (Upaya) always finds a path.
- Adopt: CAX/self-organising-systems NCA patterns (MIT/Apache) for the tissue;
  Build: this thin agent layer (no suitable OSS for Purva-Paksha security loop).
"""
import time

# Samkhya Guna classification of system state
def guna_of(phase, alive_ratio):
    if alive_ratio < 0.5:
        return "Tamas (inertia/death - revive or kill cleanly)"
    if phase in ("under-attack", "patching"):
        return "Rajas (agitation/activity - act, but verify)"
    return "Sattva (clarity/balance - monitor, prevent)"

class Prashnika:
    """Questioner - Purva Paksha: states the opponent's case strongest, then attacks it."""
    name = "Prashnika (Purva Paksha - eternal questioner)"
    def question(self, proposal, context):
        qs = [
            {"q": "Pratyaksha? What was directly observed, not inferred?", "evidence": context.get("observed")},
            {"q": "Anumana? Does the fix block the exploit class, or only this payload?", "blocks": proposal.get("summary")},
            {"q": "What breaks if this patch is wrong? Is rollback artifact ready?", "rollback": proposal.get("rollback_ready")},
            {"q": "Who authorized this force level? Could a lesser Upaya work?", "force": proposal.get("upaya")},
            {"q": "If I were the attacker, how do I bypass this in one move?", "bypass_test": context.get("bypass_test")},
        ]
        blocks = []
        if not context.get("observed"):
            blocks.append("No Pratyaksha (direct observation) - cannot heal on inference alone.")
        if not proposal.get("rollback_ready"):
            blocks.append("No rollback artifact - irreversible action forbidden.")
        return {"agent": self.name, "questions": qs, "blocks": blocks,
                "verdict": "BLOCK" if blocks else "QUESTIONED-CLEAR"}

class Margadarshi:
    """PathFinder - Upaya: Sama (persuade/monitor) -> Dana (concede/flag) -> Bheda (isolate) -> Danda (enforce/kill). Least force first."""
    name = "Margadarshi (Upaya - path finder)"
    LADDER = ["Sama: monitor + alert, no state change",
              "Dana: concede ground - feature-flag off the vulnerable path",
              "Bheda: divide - isolate container/endpoint from swarm",
              "Danda: enforce - apply patch / kill process (broker only)"]
    def find_path(self, severity, confidence):
        if severity == "probe" or confidence < 0.5:
            idx = 0
        elif severity == "leak" and confidence < 0.85:
            idx = 1
        elif severity == "leak":
            idx = 2
        else:
            idx = 3
        return {"agent": self.name, "upaya_index": idx, "path": self.LADDER[idx],
                "ladder": self.LADDER, "rule": "least force that reversibly stops the harm"}

class Vaidya:
    """Healer - Ayurveda: Pratibandhakatva (prevent manifestation) above Bala-Virodhitva (fight manifested)."""
    name = "Vaidya (Ayurvedic healer)"
    def prescribe(self, patch):
        return {"agent": self.name, "cure": patch.get("summary"),
                "prevention": "Harden terrain after cure: least-privilege, parameterized-by-default, attested image.",
                "agni_check": "Metabolism lease must be renewed; starved organism cannot heal."}

class PramanaVerifier:
    """Verifier - Nyaya: every claim tagged by evidence type; replay is Pratyaksha, Muse opinion is Shabda (weakest alone)."""
    name = "Pramana (Nyaya verifier)"
    def verify(self, replay):
        tags = {"attack_blocked": "Pratyaksha (replayed exploit)",
                "normal_ok": "Pratyaksha (replayed normal traffic)",
                "muse_opinion": "Shabda (testimony - never sufficient alone)"}
        passed = bool(replay.get("attack_blocked") and replay.get("normal_ok") and replay.get("applied"))
        return {"agent": self.name, "verdict": "PASS" if passed else "FAIL",
                "evidence_tags": tags, "rule": "Agreement is not a gate; replayed evidence is."}

class Rakshaka:
    """Guardian - Durga + Panchabhuta sensor rings."""
    name = "Rakshaka (Durga guardian)"
    RINGS = {"Akasha (space/network)": "gateway rejects malformed", "Vayu (flow/traffic)": "host contains in seconds",
             "Agni (fire/compute)": "container judges semantics", "Jala (water/data)": "DB barren of value (tokenized)",
             "Prithvi (earth/host)": "signed, attested ground"}
    def posture(self, contained, patched):
        return {"agent": self.name, "rings": self.RINGS,
                "state": f"contained={contained} patched={patched}"}

class Smriti:
    """Memory - adaptive immunity: remembers signatures so second attack is faster."""
    name = "Smriti (adaptive memory)"
    def __init__(self):
        self.signatures = []
    def remember(self, event, verdict):
        rec = {"ts": time.strftime("%H:%M:%S"), "event": event, "verdict": verdict}
        self.signatures.append(rec)
        return rec
    def recall(self, event):
        return [s for s in self.signatures if s["event"] == event]

class Orchestrator:
    """Deterministic loop owner (Ganita: bounded iteration, like Kuttaka refinement - never infinite debate)."""
    MAX_QUESTION_ROUNDS = 3
    def __init__(self):
        self.prashnika, self.marga, self.vaidya = Prashnika(), Margadarshi(), Vaidya()
        self.verifier, self.rakshaka, self.smriti = PramanaVerifier(), Rakshaka(), Smriti()
        self.trail = []
    def run_heal_cycle(self, *, observed, severity, confidence, patch, replay_fn, apply_fn, rollback_fn, preflight_fn=None):
        trail = []
        path = self.marga.find_path(severity, confidence); trail.append(path)
        # Least-force rungs do not patch: Sama monitors, Dana flags only.
        if path["upaya_index"] == 0:
            self.smriti.remember(severity, "MONITORED")
            return {"outcome": "MONITORED", "trail": trail, "path": path}
        if path["upaya_index"] == 1:
            self.smriti.remember(severity, "FLAGGED")
            return {"outcome": "FLAGGED-NO-PATCH", "trail": trail, "path": path}
        # Real rollback readiness from a pre-flight check, never hardcoded.
        rollback_ready = bool(preflight_fn()) if preflight_fn else bool(rollback_fn)
        trail.append({"agent": "Preflight", "rollback_ready": rollback_ready,
                      "prior_memory": self.smriti.recall(severity)})
        proposal = {"summary": patch.get("summary"), "rollback_ready": rollback_ready, "upaya": path["path"]}
        q = None
        for _ in range(self.MAX_QUESTION_ROUNDS):
            q = self.prashnika.question(proposal, {"observed": observed, "bypass_test": "replay will test class, not payload"})
            break
        trail.append(q)
        if q["verdict"] == "BLOCK":
            return {"outcome": "BLOCKED-BY-QUESTIONER", "trail": trail}
        rx = self.vaidya.prescribe(patch); trail.append(rx)
        applied = apply_fn()
        replay = replay_fn(applied)
        verdict = self.verifier.verify(replay); trail.append(verdict)
        if verdict["verdict"] != "PASS":
            rollback_fn()
            self.smriti.remember(severity, "FAIL-rolled-back")
            return {"outcome": "REJECTED-ROLLED-BACK", "trail": trail, "verdict": verdict, "replay": replay}
        self.smriti.remember(severity, "PASS")
        trail.append(self.rakshaka.posture(contained=True, patched=True))
        self.trail = trail
        return {"outcome": "HEALED", "trail": trail, "verdict": verdict, "path": path, "replay": replay}
