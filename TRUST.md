# Trust Boundary — What the Organisms May and May Not Do

Verify this from the repo alone. No trust in marketing claims required.

## Only mutation path
Browser/dashboard -> host broker (token-authenticated) -> canary -> verifier gate -> promotion.
The organisms (NCA/brain/agents) **propose**; the broker is the only component that applies.

## May
- Sense: read victim health, replay exploit corpora against canary twins.
- Propose: Muse (or validated fallback) patch snippets, persisted as artifacts on the shared volume.
- Promote: only after canary replay PASS (attack blocked + normal traffic OK + applied), with kill-switch epoch re-checked immediately before promotion.
- Learn: grow brain neurons/instincts from verified heals; teach peers. Only verified heals teach.
- Die: lease withdrawal (kill switch) halts sensing, patching, asking. Organisms cannot revive themselves; revive requires the operator token.

## May not
- Apply any patch without the broker token (victim fails closed 403, including when token is unset/default).
- Verify their own patch (deterministic replay gate; LLM opinion is advisory only, never flips the gate).
- Survive a restart with memory: population/brain reset on container restart (patch artifact persists). This limitation is stated, not hidden.
- Reach the network beyond the victim service and the configured Meta Model API base.
- Update themselves: updates are HMAC-signed manifests applied canary-first with health check and last-known-good rollback (`organism/control.py`); unsigned updates are rejected unapplied.

## Secrets
`BROKER_TOKEN` and `META_API_KEY` live only in `.env` (gitignored) / environment. No secret is in any image layer or this repo.

## Audit
Broker swarm log + patch artifacts (`/shared/patched_app.py`, SHA in `/api/_patch_state`) + agent trail in `/state` are the audit record. Export: `curl http://127.0.0.1:18002/state` with token-authenticated POST routes for actions.

## Scope honesty
Bundled victim is intentionally vulnerable demo code. Protecting your own application requires a per-app patch adapter (your routes, your replay corpus); the canary/broker/verifier machinery is app-agnostic, the patch templates are not magic.
