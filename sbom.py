"""Generate a minimal SBOM (component inventory) for the trust pack."""
import json
import pathlib
root = pathlib.Path(__file__).parent
comps = []
for req in sorted(root.rglob("requirements.txt")):
    for line in req.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            name, _, ver = line.partition("==")
            comps.append({"type": "library", "name": name, "version": ver or "unpinned",
                          "from": str(req.relative_to(root))})
for img in ("python:3.12-slim",):
    comps.append({"type": "container-base", "name": img})
out = {"bomFormat": "CycloneDX-lite", "components": comps}
pathlib.Path("sbom.json").write_text(json.dumps(out, indent=2))
print(f"SBOM: {len(comps)} components -> sbom.json")
