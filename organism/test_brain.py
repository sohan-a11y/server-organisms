import sys
sys.path.insert(0, ".")
from brain import Brain

# Understands seeded English/code knowledge
b = Brain("org-A")
r = b.ask("what stops sql injection that dumps all users?")
assert r["known"] and "parameterize" in r["answer"], r
print("recall seeded knowledge: OK via", r["via"])

# Unknown without LLM: queued honestly, neurons do not fake knowledge
r2 = b.ask("how to stop timing side channel in token compare?")
assert not r2["known"] and "queued" in r2["via"], r2
print("unknown honesty (queued for LLM): OK")

# With LLM teacher stub: learns, grows neurons, then remembers without LLM
calls = {"n": 0}
def fake_llm(q):
    calls["n"] += 1
    return "use constant time compare for tokens; never early exit on mismatch"
b2 = Brain("org-B", llm_ask=fake_llm)
n0 = b2.snapshot()["neurons"]
r3 = b2.ask("how to stop timing side channel in token compare?")
assert r3["known"] and r3["via"].startswith("LLM taught"), r3
n1 = b2.snapshot()["neurons"]
assert n1 > n0, (n0, n1)
r4 = b2.ask("timing side channel token compare fix?")
assert r4["known"] and r4["via"].startswith("memory"), r4
assert calls["n"] == 1, calls
print(f"LLM learn-once then remember: OK neurons {n0} -> {n1}, LLM calls {calls['n']}")

# Swarm teaching: A learns, teaches B; B grows without asking LLM
a, c = Brain("org-A"), Brain("org-C")
a.learn("xss reflected script executes in victim browser", "escape output and set content security policy", source="experience")
before = c.snapshot()["neurons"]
res = c.receive_teaching(a.teach_packet())
after = c.snapshot()["neurons"]
assert res["absorbed"] >= 1 and after > before, (res, before, after)
assert c.ask("reflected xss script fix?")["known"]
print(f"swarm teaching: OK absorbed {res['absorbed']}, neurons {before} -> {after}")

# Reasoning confidence grows on verified success, shrinks on failure
conf0 = [i["confidence"] for i in b.instincts if "sql" in i["trigger"]][0]
b.reward("sql injection", True)
conf1 = [i["confidence"] for i in b.instincts if "sql" in i["trigger"]][0]
assert conf1 > conf0
print(f"confidence growth on reward: OK {conf0} -> {conf1}")
print("BRAIN TEST PASS")
