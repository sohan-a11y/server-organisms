# Protect Your Own App (Per-App Adapter)

The organism machinery (sense -> question -> canary -> verify -> promote -> kill switch) is app-agnostic. Your app supplies one config; templates are not magic.

## What your app must provide
1. **Health + normal endpoints** — replay corpus proves normal traffic still works after a patch.
2. **Canary twin routes** — same handlers running the candidate patch (e.g. `/api/_canary/...`), isolated from live traffic.
3. **Patch webhook** — `POST` receiving `{artifact, class}` with header `X-Broker-Token: <your secret>`; it persists the artifact (file/image/config) and flips live to use it. Refuse without the token (fail closed).
4. **Exploit checks** — one URL per vuln class whose response proves the class is exploitable (marker/status), for live and canary.

Copy `adapter.example.json`, point `base_url` at your service, set `patch_token`, run:
`python -c "from organism.adapter import AppAdapter; import json; print(AppAdapter(json.load(open('adapter.example.json'))).run(open('patch.py').read()))"`

## Honest limit
The organism generates patch artifacts for the classes it knows (SQLi, broken-auth, XSS today; Muse proposes, validator checks parameterized/ownership/escaping shape). For a new class you add: template + canary check + corpus entry. The broker, verifier, lease, and rollback work unchanged.
