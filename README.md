# Server Organisms — Self-Healing Swarm for Live Servers

Organisms that **live on your servers** (not in phones, not in a simulation), sense an exploit as damage to a Neural Cellular Automata tissue, swarm, propose a patch with Muse, and heal the server — under a kill switch they do not own.

Built for the **Meta Global AI Developer Hackathon — Push the Frontier**. Track: give a machine a new capability: self-healing.

## Stranger quickstart (<10 min, your own server)

```bash
git clone <this-repo> && cd <this-repo>
./install.sh        # Windows: .\install.ps1  (generates private BROKER_TOKEN in .env)
# Optional: edit .env, set META_API_KEY=<your Meta Model API key> for live Muse, then: docker compose up -d
```

Open the dashboard (token in URL): `http://127.0.0.1:18000/?token=<BROKER_TOKEN from .env>`.
Press Launch exploit -> Organisms heal -> Kill switch. Your data never leaves this host.
Default mode in this demo is auto-heal for the bundled victim only; protecting your own app requires the per-app patch adapter (see PRODUCT_PLAN.md Step 4 status in TRUST.md).

## Run it (one command)

```bash
cp .env.example .env  # set BROKER_TOKEN to a random secret: python -c "import secrets; print(secrets.token_hex(32))"
docker compose up --build
```

Then **open http://localhost:18000/?token=<your BROKER_TOKEN> in your browser** (dashboard). Victim API: http://localhost:18001 · Organism broker: http://localhost:18002

No Docker? Run locally:

```bash
pip install flask requests
python victim-api/app.py          # terminal 1, :18001
BROKER_TOKEN=<random-secret> VICTIM_URL=http://127.0.0.1:18001 python organism/broker.py   # terminal 2, :18002 (same BROKER_TOKEN in terminal 1)
python -m http.server 18000 --directory dashboard             # terminal 3, :18000
```

## Demo (90 seconds)

1. Press **Launch exploit** — SQL injection `1 OR 1=1` dumps all user records (id/name/email); NCA grid centre dies red.
2. Press **Organisms heal** — broker contains, Muse Spark proposes parameterized-query fix, broker applies it to an isolated canary, verifier replays the exploit corpus + normal traffic on the canary; only on **PASS** is the persisted patch artifact promoted to the live server and tissue regrows. On FAIL the live server is untouched.
3. Press **Kill switch** — lease withdrawn from the control plane; organisms halt instantly.

Exploit from terminal: `python attacker/exploit.py http://localhost:18001`

## How it maps to the research architecture

| Research decision | Hackathon implementation | Production form |
|---|---|---|
| Live on host, act in container | Host broker process + per-service NCA grid | DaemonSet (Tetragon/Falco eBPF) + sidecar cells |
| Stop: contain at host, judge in container | Broker flags/contians, NCA+Muse judges semantics | eBPF kill/isolate → semantic patch |
| Muse = brain | `organism/muse_client.py`: proposer + separate verifier prompts via Meta Model API (`META_API_KEY`; deterministic fallback keeps demo unblocked) | Muse Spark / Spark Open on Baseten/Modal |
| Patcher ≠ verifier | Two isolated Muse contexts + live traffic replay | Independent verifier service, frozen corpus |
| Kill switch outside organism | Lease flag held by broker/control plane, checked on every action | Out-of-band control plane, credential revocation |
| Swarm language | XOR+base64 encoded log (obfuscation only, not encryption) + plain intent for the demo; mTLS + capability tokens in production design | mTLS (SPIFFE) + Verifiable Capability Tokens |

## Built during the hackathon vs reused

**Built during hackathon (our novelty):** security-state encoding as NCA damage, host-broker containment/promotion logic, leased kill-switch, Muse proposer/verifier split wired to live replay, swarm log, dashboard theatre.
**Reused (cited, licences preserved):** Growing NCA concept from Mordvintsev et al. 2020 — reference code `google-research/self-organising-systems` (Apache 2.0); CAX library design (Faldor & Cully 2024). No Mayhem/GenProg code reused (proprietary/research). See novelty statement in research notes: components are prior art; the server-resident NCA security-tissue integration is the contribution.

## Novelty claim

Prior work separately shows NCA regenerating patterns, autonomous patching in tournaments (DARPA CGC), and eBPF agents blocking attacks. No prior system encodes live server security posture as NCA state, defines exploit damage as pattern corruption, and regenerates a verified patch under leased, externally killable organisms. This demo tests that integration on one vulnerability (SQL injection).

## Layout

- `victim-api/app.py` — deliberately vulnerable API (patched mode is parameterized)
- `organism/nca.py` — local-rule NCA tissue · `organism/muse_client.py` — Muse proposer/verifier · `organism/broker.py` — host broker, lease, swarm
- `dashboard/index.html` — live organism theatre · `attacker/exploit.py` — replayable exploit
- `DEMO_VIDEO_SCRIPT.md` — 3-minute submission video beats

## Safety

Demo only: `victim-api` is intentionally vulnerable. Never deploy it. The broker writes a persisted patched-source artifact to the shared volume (`PATCH_FILE`, default `/shared/patched_app.py` in Docker); the victim serves the parameterized query only while that artifact exists, so the patch survives a victim restart. `BROKER_TOKEN` must be a random secret (see `.env.example`); unset/default tokens fail closed.
