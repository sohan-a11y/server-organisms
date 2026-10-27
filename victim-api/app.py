import os
import sys
import sqlite3
import threading
import hashlib
from flask import Flask, jsonify, request

app = Flask(__name__)

@app.after_request
def cors(r):
    r.headers["Access-Control-Allow-Origin"] = "*"
    r.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Broker-Token"
    r.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return r

LOG = os.environ.get("SHARED_LOG", "/shared/access.log")
# DB and patch artifacts live on a shared/persistent volume in Docker
# (/shared) so a container restart does not silently revert the patch.
# Locally both processes share the same host temp dir, which also
# survives a process restart.
_SHARED_BASE = os.environ.get("SHARED_DIR") or ("/shared" if os.name == "posix" and os.path.isdir("/shared") else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "shared-patch"))
_PATCH_DEFAULT = os.path.join(_SHARED_BASE, "patched_app.py")
PATCH_FILE = os.environ.get("PATCH_FILE", _PATCH_DEFAULT)
CANARY_PATCH_FILE = os.environ.get("CANARY_PATCH_FILE", PATCH_FILE + ".canary")
DB = os.environ.get("VICTIM_DB", "/tmp/users.db")
_lock = threading.Lock()
BROKER_TOKEN = os.environ.get("BROKER_TOKEN", "")
_TOKEN_SECURE = bool(BROKER_TOKEN) and BROKER_TOKEN != "demo-broker-token"
if not _TOKEN_SECURE:
    print("WARNING: BROKER_TOKEN is unset or is the public demo default. "
          "Protected endpoints fail closed (403). Set BROKER_TOKEN to a "
          "random secret (see .env.example) for the heal flow to work.",
          file=sys.stderr)

def _authed():
    # Fail closed when no secure token is configured.
    if not _TOKEN_SECURE:
        return False
    return request.headers.get("X-Broker-Token") == BROKER_TOKEN

USERS = [
    (1, "Asha Rao", "asha@example.com", "INTERNAL-NOTE-ASHA-SALARY-82L"),
    (2, "Ravi Kumar", "ravi@example.com", "INTERNAL-NOTE-RAVI-PASSPORT-991"),
    (3, "Meera Iyer", "meera@example.com", "INTERNAL-NOTE-MEERA-HEALTH-447"),
]

def init_db():
    if os.path.exists(DB):
        os.remove(DB)
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE users (id INTEGER, name TEXT, email TEXT, secret TEXT)")
    con.executemany("INSERT INTO users VALUES (?,?,?,?)", USERS)
    con.commit(); con.close()

def log(msg):
    try:
        d = os.path.dirname(LOG)
        if d:
            os.makedirs(d, exist_ok=True)
        safe = str(msg).replace("\r", " ").replace("\n", " ")
        with _lock, open(LOG, "a") as f:
            f.write(safe + "\n")
    except Exception:
        pass

def _patch_active(path):
    """A patch is real only if a persisted parameterized source artifact exists."""
    try:
        with open(path) as f:
            content = f.read()
        return "WHERE id=?" in content and "execute(" in content
    except Exception:
        return False

def is_patched():
    return _patch_active(PATCH_FILE)

def is_canary_patched():
    return _patch_active(CANARY_PATCH_FILE)

def _query(user_id, patched):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        if patched:
            rows = con.execute("SELECT id,name,email FROM users WHERE id=?", (user_id,)).fetchall()
        else:
            q = f"SELECT id,name,email FROM users WHERE id = {user_id}"
            rows = con.execute(q).fetchall()
        return [dict(r) for r in rows], None
    except Exception:
        return None, "query failed"
    finally:
        con.close()

@app.get("/health")
def health():
    return jsonify(status="ok", patched=is_patched(),
                   mode="patched" if is_patched() else "vulnerable")

@app.get("/api/users")
def list_users():
    log(f"GET /api/users ip={request.remote_addr}")
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute("SELECT id,name,email FROM users").fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        con.close()

@app.get("/api/user/<user_id>")
def get_user(user_id):
    log(f"GET /api/user/{user_id} ip={request.remote_addr} ua={request.user_agent}")
    rows, err = _query(user_id, is_patched())
    if err:
        return jsonify(error="invalid user id"), 400
    return jsonify(rows)

# --- Canary instance: isolated patch target verified BEFORE live promotion ---
@app.get("/api/_canary/user/<user_id>")
def canary_get_user(user_id):
    rows, err = _query(user_id, is_canary_patched())
    if err:
        return jsonify(error="invalid user id"), 400
    return jsonify(rows)

@app.get("/api/_canary_state")
def canary_state():
    return jsonify(patched=is_canary_patched())

@app.post("/api/_canary_apply_patch")
def canary_apply_patch():
    if not _authed():
        return jsonify(error="forbidden: broker token required"), 403
    if not is_canary_patched():
        return jsonify(error="no canary patch artifact on shared volume"), 409
    log("CANARY_PATCH_APPLIED by=organism-broker")
    return jsonify(patched=True, canary=True)

@app.post("/api/_canary_reset")
def canary_reset():
    if not _authed():
        return jsonify(error="forbidden: broker token required"), 403
    try:
        if os.path.exists(CANARY_PATCH_FILE):
            os.remove(CANARY_PATCH_FILE)
    except Exception:
        pass
    log("CANARY_RESET to=vulnerable")
    return jsonify(patched=False, canary=True)

@app.get("/api/_patch_state")
def patch_state():
    h = None
    try:
        with open(PATCH_FILE, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        pass
    return jsonify(patched=is_patched(), patch_file=PATCH_FILE, patch_sha=h)

@app.post("/api/_apply_patch")
def apply_patch():
    if not _authed():
        return jsonify(error="forbidden: broker token required"), 403
    # Promotion is real only when the broker has written a persisted
    # patched-source artifact to the shared volume first.
    if not is_patched():
        return jsonify(error="no persisted patch artifact on shared volume; refusing to flip flag"), 409
    log("PATCH_APPLIED by=organism-broker artifact=" + PATCH_FILE)
    return jsonify(patched=True)

@app.post("/api/_reset")
def reset():
    if not _authed():
        return jsonify(error="forbidden: broker token required"), 403
    for p in (PATCH_FILE, CANARY_PATCH_FILE, PATCH_FILE + ".auth", PATCH_FILE + ".xss", CANARY_PATCH_FILE + ".auth", CANARY_PATCH_FILE + ".xss"):
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass
    log("RESET to=vulnerable")
    return jsonify(patched=False)


# --- Class 2: broken authorization (IDOR) ---
AUTH_PATCH_FILE = PATCH_FILE + ".auth"
XSS_PATCH_FILE = PATCH_FILE + ".xss"
def _active(path, marker):
    try:
        return marker in open(path).read()
    except Exception:
        return False
def is_auth_patched():
    return _active(AUTH_PATCH_FILE, "check ownership")
def is_xss_patched():
    return _active(XSS_PATCH_FILE, "escape output")

def _profile(uid, as_user, patched):
    row = next((u for u in USERS if str(uid).isdigit() and u[0] == int(uid)), None)
    if row is None:
        return jsonify(error="not found"), 404
    if patched and str(as_user) != str(uid):
        return jsonify(error="forbidden: ownership check"), 403
    return jsonify(id=row[0], name=row[1], email=row[2], secret=row[3])

@app.get("/api/profile/<uid>")
def profile(uid):
    return _profile(uid, request.args.get("as_user", ""), is_auth_patched())

@app.get("/api/_canary/profile/<uid>")
def canary_profile(uid):
    return _profile(uid, request.args.get("as_user", ""), _active(CANARY_PATCH_FILE + ".auth", "check ownership"))

def _comment(name, patched):
    import html as _h
    shown = _h.escape(name) if patched else name
    return f"<html><body>hello {shown}</body></html>", 200, {"Content-Type": "text/html"}

@app.get("/api/comment")
def comment():
    return _comment(request.args.get("name", ""), is_xss_patched())

@app.get("/api/_canary/comment")
def canary_comment():
    return _comment(request.args.get("name", ""), _active(CANARY_PATCH_FILE + ".xss", "escape output"))

@app.post("/api/_apply_class_patch")
def apply_class_patch():
    if not _authed():
        return jsonify(error="forbidden: broker token required"), 403
    cls = (request.get_json(silent=True) or {}).get("class", "")
    targets = {"sql": (PATCH_FILE, "WHERE id=?"), "auth": (AUTH_PATCH_FILE, "check ownership"), "xss": (XSS_PATCH_FILE, "escape output")}
    canaries = {"sql": (CANARY_PATCH_FILE, "WHERE id=?"), "auth": (CANARY_PATCH_FILE + ".auth", "check ownership"), "xss": (CANARY_PATCH_FILE + ".xss", "escape output")}
    if cls not in targets:
        return jsonify(error="unknown class"), 400
    src, marker = canaries[cls]
    dst, _ = targets[cls]
    try:
        content = open(src).read()
    except Exception:
        return jsonify(error="no canary artifact for class"), 409
    if marker not in content:
        return jsonify(error="canary artifact invalid for class"), 409
    if cls == "sql":
        return jsonify(patched=True, promoted="sql-via-canary-state")
    open(dst, "w").write(content)
    return jsonify(patched=True, **{"class": cls})

if __name__ == "__main__":
    init_db()
    log("VICTIM_START mode=" + ("patched" if is_patched() else "vulnerable"))
    app.run(host="0.0.0.0", port=18001)
