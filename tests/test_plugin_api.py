"""Regression tests for SMF App Launcher start/open path."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

import plugin_api as api


def _fake_app(tmp_path: Path, name: str = "paste-to-skill") -> Path:
    app = tmp_path / name
    app.mkdir()
    (app / "index.html").write_text("<html></html>", encoding="utf-8")
    (app / "vite.config.ts").write_text("export default {}", encoding="utf-8")
    (app / "package.json").write_text(
        json.dumps({"name": name, "scripts": {"dev": "vite"}}),
        encoding="utf-8",
    )
    return app


def test_dev_url_does_not_claim_an_unrelated_open_port(tmp_path, monkeypatch):
    """sparkDash (or any other Vite) on 5173 must not look like a kit app."""
    app = _fake_app(tmp_path)
    monkeypatch.setattr(api, "_port_open", lambda port: port == 5173)
    api._PROCS.clear()

    assert api._dev_url(app) is None


def test_dev_url_returns_only_the_port_this_launcher_started(tmp_path, monkeypatch):
    app = _fake_app(tmp_path, "skill-lint")
    monkeypatch.setattr(api, "_port_open", lambda port: port == 5242)
    api._PROCS.clear()
    api._PROCS["skill-lint"] = {"port": 5242, "pid": 0}

    assert api._dev_url(app) == "http://127.0.0.1:5242/"


def test_merge_catalog_includes_uncloned_kit_apps():
    extra = {
        "paste-to-skill": {
            "title": "Paste → Skill",
            "description": "SOP to SKILL.md",
            "vercel_url": "",
        }
    }
    apps = api.merge_catalog({}, extra)
    by_name = {a["name"]: a for a in apps}
    assert "paste-to-skill" in by_name
    rec = by_name["paste-to-skill"]
    assert rec["local_path"] == ""
    assert rec["cloned"] is False
    assert rec["dev_url"] in (None, "")
    assert rec["title"] == "Paste → Skill"
    assert len(apps) >= 10


def test_merge_catalog_keeps_local_clone_metadata(tmp_path):
    extra = {"paste-to-skill": {"title": "Paste → Skill", "description": "x", "vercel_url": ""}}
    found = {
        "paste-to-skill": {
            "name": "paste-to-skill",
            "title": "paste-to-skill",
            "description": "",
            "local_path": str(tmp_path),
            "dev_url": None,
            "htmlUrl": "https://github.com/smfworks/paste-to-skill",
        }
    }
    apps = api.merge_catalog(found, extra)
    rec = next(a for a in apps if a["name"] == "paste-to-skill")
    assert rec["cloned"] is True
    assert rec["local_path"] == str(tmp_path)
    assert rec["title"] == "Paste → Skill"


def test_kit_name_rejects_path_traversal():
    assert api.safe_kit_name("paste-to-skill") == "paste-to-skill"
    assert api.safe_kit_name("../etc/passwd") is None
    assert api.safe_kit_name("smfworks-site") is None


def test_merge_catalog_ignores_extra_names_not_in_kit():
    extra = {"evil-app": {"title": "Evil", "description": "x", "vercel_url": ""}}
    apps = api.merge_catalog({}, extra)
    names = {a["name"] for a in apps}
    assert "evil-app" not in names
    assert "paste-to-skill" in names
