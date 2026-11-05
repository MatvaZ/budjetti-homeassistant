"""Versio on samana VERSION-tiedostossa ja manifest.json:ssa (julkaisu luetaan VERSION-tiedostosta)."""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent


def test_version_matches_manifest():
    version = (ROOT / "VERSION").read_text().strip()
    manifest = json.loads((ROOT / "custom_components" / "budjetti" / "manifest.json").read_text())
    assert version == manifest["version"]
    assert len(version.split(".")) == 3 and all(p.isdigit() for p in version.split("."))
