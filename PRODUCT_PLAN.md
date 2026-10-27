# Product Plan: Server Organisms Anyone Can Keep in Their Systems
*Blueprint-style stepped plan | Research-grounded | Each step cold-start executable*

## The best way (from everything known)

Do NOT sell "an organism." Sell **one-command protection for one server stack**, the way every successful agent product works: EDR ships MSI/installer + site token and auto-updates ([SentinelOne via Automox](https://www.automox.com/worklets/install-sentinelone-agent-windows), [Rapid7 agent](https://help.rapid7.com/insightidr/content/endpoint-monitoring/installing-endpoint-monitor.html)); Kubernetes security ships a Helm DaemonSet ([Tetragon Helm](https://platform-monkey.com/guides/k8s-security-hardening-baseline), [Falco Helm](https://www.gocodeo.com/post/detecting-runtime-threats-in-kubernetes-with-falco)). Agent-based = real-time + patching power but deployment friction; agentless = easy but scan-delayed ([Rapid7 Agent vs Agentless](https://blog.rapid7.com/2021/11/02/a-matter-of-perspective-agent-based-and-agentless-approaches-to-cloud-security-part-2-2)). Your differentiator is resident + self-healing, so you must pay agent friction and erase it with onboarding: enrollment happens once per install, then short-lived tokens refresh ([Agent Enrollment](https://www.agentprovider.dev/docs/enrollment.html)). Updates must be signed, canary (<1% first), with rollback to last-known-good ([OTA Canary/Rollback](https://www.trendmicro.com/vinfo/ru/security/news/cybercrime-and-digital-threats/agentic-edge-ai-development-tools-and-workflows), [Secure OTA](https://beefed.ai/en/secure-ota-updates-anti-rollback)). Trust sells security products: action broker as only mutation path + dry-run + rollback + kill switch as public trust boundary ([Argus Trust Audit](https://dev.to/victor_guerillot_aeecd294/a-public-trust-boundary-a-remote-testing-packet-for-agent-patches-fn3) style).

**Product shape (v1):** Docker Compose / Helm install on the customer's own server (their data never leaves), Muse key = BYO or hosted control plane later, dashboard = local, mode default = *suggest* (human approves), auto-heal unlocked per endpoint.

## Steps (dependency order)

1. **Truth-in-demo** (no deps): real canary instance; patch = generated code artifact applied to canary, verified, then promoted. Exit: verifier FAIL leaves live traffic untouched (test proves it).
2. **Installable package** (deps: 1): `install.sh` + Compose/Helm with enrollment token, pinned images, non-root where possible, `.env` secrets. Exit: fresh VM -> protected in <10 min by a stranger following README only.
3. **Control plane lite** (deps: 2): signed config, heartbeat, signed auto-update with canary + rollback, kill switch remote. Exit: bad update rolls back automatically in test.
4. **Generalize sensing** (deps: 1): log/API watcher interface + 3 vuln classes (SQLi, broken auth, XSS) with replay corpora. Exit: each class exploit->heal PASS in CI.
5. **Trained NCA** (deps: 4, parallel with 3): CAX-trained genome replaces hand rule; fitness = measured heal rate. Exit: trained >= hand-rule on damage-localization benchmark.
6. **Trust pack** (deps: 3): audit log export, SBOM, signed releases, docs of broker boundary. Exit: third party can verify what organism may/may not do from repo alone.

## Anti-patterns (do not do)
- Hosted-only SaaS first (data-trust friction kills adoption); custom installer binary before Compose proves value; auto-heal ON by default; organism updating itself without signed canary.
