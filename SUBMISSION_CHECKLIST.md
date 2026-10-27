# Submission Checklist — Meta Global AI Developer Hackathon (due Nov 4, 9:00 PM ET)

- [ ] Claim $150 Meta Model API credits (each team member individually, by Nov 4 9PM ET) and set `META_API_KEY` in `.env`; re-run heal to capture live Muse Spark trace
- [ ] `docker compose up --build` clean run; dashboard at http://127.0.0.1:18000
- [ ] `python smoke_test.py` → SMOKE PASS (exploit / sense / heal PASS / blocked / kill)
- [ ] `python attacker/exploit.py http://127.0.0.1:18001` before heal leaks, after heal blocked
- [ ] Record 3-minute video per `DEMO_VIDEO_SCRIPT.md` (one clean take + backup)
- [ ] Push public GitHub repo (this folder); judges must see Built-vs-Reused section in README
- [ ] Submit one project entry via CV platform; link repo + accessible video; list all team members (max 4)
- [ ] Post 30-sec heal clip to X for Most Viral ($20K) and submit post link
- [ ] Optional bonus flags: Best Agentic Use-Case (proposer/verifier agents), Best Build on Open Weights (Spark Open via Baseten `meta-models/muse-spark-open-1026`)

Rules reminder: new work only must be identifiable; do not present the intentionally vulnerable demo API as a production product.
