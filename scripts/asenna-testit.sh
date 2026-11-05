#!/usr/bin/env bash
# Asentaa testiriippuvuudet aktiiviseen Python-ympäristöön.
#   scripts/asenna-testit.sh              # nykyinen testattava HA (requirements_test.txt)
#   scripts/asenna-testit.sh vanhin       # vähimmäisversio HA 2025.3 (requirements_test_min.txt)
# Lopuksi asennetaan HA:n frontend-paketti siinä versiossa, jota asennettu HA vaatii
# (integraatio riippuu frontend-komponentista).
set -euo pipefail
cd "$(dirname "$0")/.."
req=requirements_test.txt
[ "${1:-}" = "vanhin" ] && req=requirements_test_min.txt
python -m pip install -r "$req"
frontend=$(python - <<'PY'
import importlib.util, json, pathlib
spec = importlib.util.find_spec("homeassistant.components.frontend")
print(json.loads((pathlib.Path(spec.origin).parent / "manifest.json").read_text())["requirements"][0])
PY
)
python -m pip install "$frontend"
