import os, sys, tempfile
sys.path.insert(0, ".")
from control import apply_update, heartbeat, sign

S = "test-secret"
with tempfile.TemporaryDirectory() as d:
    cur = os.path.join(d, "organism.py")
    open(cur, "w").write("v1-good")
    good = b"v2-good"
    ok, detail = apply_update(S, {"version": "2", "content": good.decode(), "sig": sign(S, good)}, cur, lambda p: True)
    assert ok == "APPLIED" and open(cur).read() == "v2-good", (ok, detail)
    print("signed update applied: OK")
    bad = b"v3-evil"
    ok2, _ = apply_update(S, {"version": "3", "content": bad.decode(), "sig": "deadbeef"}, cur, lambda p: True)
    assert ok2 == "REJECTED-BAD-SIGNATURE" and open(cur).read() == "v2-good"
    print("unsigned update rejected, live untouched: OK")
    sick = b"v4-sick"
    ok3, _ = apply_update(S, {"version": "4", "content": sick.decode(), "sig": sign(S, sick)}, cur, lambda p: False)
    assert ok3 == "ROLLED-BACK" and open(cur).read() == "v2-good"
    print("unhealthy canary rolled back to last-known-good: OK")
    assert heartbeat(S, "2")["sig"]
    print("CONTROL TEST PASS")
