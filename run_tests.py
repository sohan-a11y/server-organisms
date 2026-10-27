"""Full test suite: unit (nca/brain/life/agents) + live loop. Run: python run_tests.py"""
import subprocess, sys

SUITE = [
    ("unit smoke", [sys.executable, "smoke_unit.py"]),
    ("brain", [sys.executable, "organism/test_brain.py"]),
    ("life", [sys.executable, "organism/test_life.py"]),
    ("agents", [sys.executable, "organism/test_agents.py"]),
    ("canary+token", [sys.executable, "organism/test_canary.py"]),
    ("classes", [sys.executable, "organism/test_classes.py"]),
    ("control", [sys.executable, "organism/test_control.py"]),
    ("trained-nca", [sys.executable, "organism/train_nca.py"]),
    ("persistence", [sys.executable, "organism/test_persistence.py"]),
    ("adapter", [sys.executable, "organism/test_adapter.py"]),
    ("live loop", [sys.executable, "smoke_test.py"]),
]
failed = []
for name, cmd in SUITE:
    print(f"\n=== {name}: {' '.join(cmd)}")
    if subprocess.run(cmd).returncode != 0:
        failed.append(name)
print("\nRESULT:", "FAIL " + str(failed) if failed else "ALL PASS")
sys.exit(1 if failed else 0)
