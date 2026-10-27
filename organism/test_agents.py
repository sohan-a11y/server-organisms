import sys
sys.path.insert(0, ".")
from agents import Orchestrator, Prashnika, Margadarshi, guna_of

# PathFinder: least force first
m = Margadarshi()
assert m.find_path("probe", 0.3)["upaya_index"] == 0
assert m.find_path("leak", 0.95)["upaya_index"] == 2
print("Margadarshi Upaya ladder: OK")

# Questioner blocks without direct observation or rollback
q = Prashnika()
assert q.question({"summary": "x", "rollback_ready": False}, {"observed": None})["verdict"] == "BLOCK"
assert q.question({"summary": "x", "rollback_ready": True}, {"observed": "log line"})["verdict"] == "QUESTIONED-CLEAR"
print("Prashnika Purva Paksha BLOCK/CLEAR: OK")

# Full cycle heals on PASS, rolls back on FAIL
o = Orchestrator()
ok = o.run_heal_cycle(observed="leak seen", severity="leak", confidence=0.95,
    patch={"summary": "parameterize"}, apply_fn=lambda: True,
    replay_fn=lambda a: {"attack_blocked": True, "normal_ok": True, "applied": a},
    rollback_fn=lambda: None)
assert ok["outcome"] == "HEALED", ok
rolled = {"v": False}
bad = o.run_heal_cycle(observed="leak seen", severity="leak", confidence=0.95,
    patch={"summary": "parameterize"}, apply_fn=lambda: True,
    replay_fn=lambda a: {"attack_blocked": False, "normal_ok": True, "applied": a},
    rollback_fn=lambda: rolled.update(v=True))
assert bad["outcome"] == "REJECTED-ROLLED-BACK" and rolled["v"]
print("Orchestrator HEALED / REJECTED-ROLLED-BACK: OK")
assert guna_of("healthy", 0.9).startswith("Sattva")
print("AGENTS TEST PASS")
