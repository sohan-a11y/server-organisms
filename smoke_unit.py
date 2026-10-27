import os, sys
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
sys.path.insert(0, "organism")
sys.path.insert(0, "victim-api")

# NCA tissue
from nca import NCAGrid
g = NCAGrid()
alive0 = g.snapshot()["alive_cells"]
g.exploit(1.0)
for _ in range(5):
    g.step()
alive_damaged = g.snapshot()["alive_cells"]
g.heal_all()
for _ in range(30):
    g.step()
alive_healed = g.snapshot()["alive_cells"]
assert alive_healed >= alive_damaged, (alive0, alive_damaged, alive_healed)
print("NCA step/heal: OK, alive", alive_healed)

# Muse fallback patcher/verifier
import muse_client
p = muse_client.propose_patch("test damage")
assert "parameteriz" in p["summary"].lower()
v = muse_client.verify_patch({"attack_blocked": True, "normal_ok": True, "applied": True})
assert v["verdict"] == "PASS", v
v_noapply = muse_client.verify_patch({"attack_blocked": True, "normal_ok": True, "applied": False})
assert v_noapply["verdict"] == "FAIL", v_noapply
v2 = muse_client.verify_patch({"attack_blocked": False, "normal_ok": True, "applied": True})
assert v2["verdict"] == "FAIL"
print("Muse proposer/verifier (fallback): OK ->", p["summary"])

# Victim SQL logic without sockets: parameterized blocks injection
import sqlite3
con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE users (id INTEGER, name TEXT, email TEXT)")
con.executemany("INSERT INTO users VALUES (?,?,?)", [(1, "A", "a@x"), (2, "B", "b@x")])
vuln = con.execute("SELECT * FROM users WHERE id = 1 OR 1=1").fetchall()
fixed = con.execute("SELECT * FROM users WHERE id=?", ("1 OR 1=1",)).fetchall()
assert len(vuln) == 2 and len(fixed) == 0
print(f"SQL demo: vulnerable returns {len(vuln)} rows, parameterized returns {len(fixed)} rows: OK")
print("UNIT SMOKE PASS (socket smoke requires unsandboxed run: python smoke_test.py)")
