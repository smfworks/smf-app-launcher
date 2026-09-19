"""Regression tests for SMF App Launcher start/open/stop path."""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

import plugin_api as api


def _body(resp) -> dict:
    return json.loads(resp.body)


def _fake_app(tmp_path: Path, name: str = "paste-to-skill") -> Path:
    app = tmp_path / name
    app.mkdir(parents=True)
    (app / "index.html").write_text("<html></html>", encoding="utf-8")
    (app / "vite.config.ts").write_text("export default {}", encoding="utf-8")
    (app / "package.json").write_text(
        json.dumps({"name": name, "scripts": {"dev": "vite"}}),
        encoding="utf-8",
    )
    return app


@pytest.fixture(autouse=True)
def _reset_module_state():
    api._PROCS.clear()
    api._README_CACHE = None
    yield
    api._PROCS.clear()
    api._README_CACHE = None


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    root = tmp_path / "smf-apps"
    root.mkdir()
    monkeypatch.setattr(api, "_clone_root", lambda: root)
    monkeypatch.setattr(api, "_home", lambda: tmp_path)
    monkeypatch.setattr(api, "_discover_owned", lambda: {})
    monkeypatch.setattr(api, "fetch_readme_extra", lambda: {})

    def owned_from_procs(pid: int):
        for name, rec in list(api._PROCS.items()):
            if int(rec.get("pid") or 0) == pid:
                return {
                    "name": name,
                    "pid": pid,
                    "port": int(rec["port"]),
                    "pgid": int(rec.get("pgid") or pid),
                }
        return None

    monkeypatch.setattr(api, "_owned_vite_rec", owned_from_procs)
    return root


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
    assert len(apps) >= 15
    for name in (
        "eval-scorecard",
        "persona-card",
        "session-timeline",
        "handoff-slip",
        "constraint-card",
    ):
        assert name in by_name
        assert name in api.KIT


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


def test_list_apps_is_sync():
    assert not inspect.iscoroutinefunction(api.list_apps)
    assert not inspect.iscoroutinefunction(api.start_app)
    assert not inspect.iscoroutinefunction(api.stop_app)


def test_scan_clones_ignores_projects_checkout(isolated, tmp_path):
    _fake_app(tmp_path / "Projects", "paste-to-skill")
    _fake_app(isolated, "skill-lint")
    found = api._scan_clones()
    assert "paste-to-skill" not in found
    assert "skill-lint" in found
    assert found["skill-lint"]["local_path"] == str((isolated / "skill-lint").resolve())


def test_ensure_clone_does_not_use_projects_tree(isolated, tmp_path, monkeypatch):
    _fake_app(tmp_path / "Projects", "paste-to-skill")
    called = {}

    class Failed:
        returncode = 1
        stderr = "denied"
        stdout = ""

    def fake_run(cmd, **kwargs):
        called["cmd"] = cmd
        return Failed()

    monkeypatch.setattr(api.subprocess, "run", fake_run)
    path, err = api.ensure_clone("paste-to-skill")
    assert path is None
    assert err
    assert called["cmd"][0] == "git"
    assert str(isolated / "paste-to-skill") in called["cmd"]


def test_ensure_clone_uses_existing_smf_apps_copy(isolated, tmp_path, monkeypatch):
    dest = _fake_app(isolated, "paste-to-skill")
    _fake_app(tmp_path / "Projects", "paste-to-skill")

    def boom(*_a, **_k):
        raise AssertionError("must not git clone when smf-apps copy exists")

    monkeypatch.setattr(api.subprocess, "run", boom)
    path, err = api.ensure_clone("paste-to-skill")
    assert err is None
    assert path == dest.resolve()


def test_npm_nvm_prefers_v20_over_v9(tmp_path, monkeypatch):
    nvm = tmp_path / ".nvm" / "versions" / "node"
    for ver in ("v9.0.0", "v20.11.0", "v18.20.0"):
        bin_dir = nvm / ver / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "npm").write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr(api, "_home", lambda: tmp_path)
    monkeypatch.setattr(api.shutil, "which", lambda _name: None)
    picked = api._npm()
    assert "v20.11.0" in picked
    assert "v9.0.0" not in picked


def test_readme_fetch_is_cached(monkeypatch):
    calls = {"n": 0}
    md = (
        "## Try these (viral apps)\n\n"
        "| App | What | Demo | Repo |\n"
        "| --- | --- | --- | --- |\n"
        "| Paste | SOP | x | [paste-to-skill](https://github.com/smfworks/paste-to-skill) |\n"
    )

    class FakeResp:
        def read(self):
            return md.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    def fake_urlopen(*_a, **_k):
        calls["n"] += 1
        return FakeResp()

    monkeypatch.setattr(api.urllib.request, "urlopen", fake_urlopen)
    api._README_CACHE = None
    first = api.fetch_readme_extra()
    second = api.fetch_readme_extra()
    assert calls["n"] == 1
    assert first == second
    assert "paste-to-skill" in first


def test_start_reuses_already_running_port(isolated, monkeypatch):
    _fake_app(isolated, "paste-to-skill")
    api._PROCS["paste-to-skill"] = {"port": 5241, "pid": 4242, "pgid": 4242}
    monkeypatch.setattr(api, "_port_open", lambda port: port == 5241)
    monkeypatch.setattr(api, "_proc_alive", lambda pid: pid == 4242)
    monkeypatch.setattr(api, "ensure_npm_install", lambda _path: None)

    def boom(*_a, **_k):
        raise AssertionError("must not spawn a second vite")

    monkeypatch.setattr(api.subprocess, "Popen", boom)
    body = _body(api.start_app("paste-to-skill"))
    assert body["ok"] is True
    assert body["url"] == "http://127.0.0.1:5241/"


def test_stop_clears_state_and_kills(isolated, monkeypatch):
    killed = []
    api._PROCS["skill-lint"] = {"port": 5267, "pid": 77, "pgid": 77}
    monkeypatch.setattr(api, "_port_open", lambda port: port == 5267)
    monkeypatch.setattr(
        api,
        "_kill_pg",
        lambda pgid, pid, wait_sec=2.0: killed.append((pgid, pid)),
    )
    body = _body(api.stop_app("skill-lint"))
    assert body["ok"] is True
    assert body["stopped"] is True
    assert "skill-lint" not in api._PROCS
    assert killed == [(77, 77)]
    state = json.loads((isolated / ".state.json").read_text(encoding="utf-8"))
    assert "skill-lint" not in state


def test_hydrate_reaps_duplicate_vite(tmp_path, monkeypatch):
    root = tmp_path / "smf-apps"
    root.mkdir()
    monkeypatch.setattr(api, "_clone_root", lambda: root)
    killed = []
    monkeypatch.setattr(
        api,
        "_discover_owned",
        lambda: {
            "agent-contract": [
                {"name": "agent-contract", "pid": 11, "port": 5274, "pgid": 11},
                {"name": "agent-contract", "pid": 22, "port": 5275, "pgid": 22},
            ]
        },
    )
    monkeypatch.setattr(
        api,
        "_kill_pg",
        lambda pgid, pid, wait_sec=2.0: killed.append(pid),
    )
    monkeypatch.setattr(
        api,
        "_load_state",
        lambda: {"agent-contract": {"port": 5274, "pid": 11, "pgid": 11}},
    )
    monkeypatch.setattr(
        api,
        "_proc_cmdline",
        lambda pid: b"node vite --port 5274" if pid == 11 else b"node vite --port 5275",
    )
    api._PROCS.clear()
    api._hydrate_procs()
    assert api._PROCS["agent-contract"]["port"] == 5274
    assert 22 in killed
    assert 11 not in killed


def test_kill_pg_missing_pid_does_not_raise():
    api._kill_pg(99999999, 99999999, wait_sec=0.01)


def test_stop_rejects_unknown_app():
    body = _body(api.stop_app("../etc/passwd"))
    assert body["ok"] is False
    assert "viral-kit" in body["error"]


def test_hydrate_merges_disk_state_with_memory(isolated, monkeypatch):
    api._PROCS["paste-to-skill"] = {"port": 5241, "pid": 50, "pgid": 50}
    (isolated / ".state.json").write_text(
        json.dumps({
            "paste-to-skill": {"port": 5241, "pid": 50, "pgid": 50},
            "skill-lint": {"port": 5267, "pid": 60, "pgid": 60},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        api,
        "_discover_owned",
        lambda: {
            "skill-lint": [{"name": "skill-lint", "pid": 60, "port": 5267, "pgid": 60}],
        },
    )
    monkeypatch.setattr(api, "_port_open", lambda port: port in (5241, 5267))
    monkeypatch.setattr(
        api,
        "_owned_vite_rec",
        lambda pid: {
            50: {"name": "paste-to-skill", "pid": 50, "port": 5241, "pgid": 50},
            60: {"name": "skill-lint", "pid": 60, "port": 5267, "pgid": 60},
        }.get(pid),
    )
    api._hydrate_procs()
    assert api._PROCS["paste-to-skill"]["port"] == 5241
    assert api._PROCS["skill-lint"]["port"] == 5267


def test_hydrate_rejects_reused_state_pid(isolated, monkeypatch):
    (isolated / ".state.json").write_text(
        json.dumps({"paste-to-skill": {"port": 5241, "pid": 50, "pgid": 50}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(api, "_port_open", lambda port: port == 5241)
    monkeypatch.setattr(api, "_proc_alive", lambda pid: pid == 50)
    monkeypatch.setattr(api, "_owned_vite_rec", lambda _pid: None)
    api._hydrate_procs()
    assert "paste-to-skill" not in api._PROCS


def test_ensure_clone_replaces_outside_symlink(isolated, tmp_path, monkeypatch):
    target = _fake_app(tmp_path / "Projects", "paste-to-skill")
    dest = isolated / "paste-to-skill"
    dest.symlink_to(target)

    def fake_run(cmd, **_kwargs):
        assert cmd[0] == "git"
        assert not dest.exists()
        _fake_app(isolated, "paste-to-skill")
        class Ok:
            returncode = 0
            stderr = ""
            stdout = ""
        return Ok()

    monkeypatch.setattr(api.subprocess, "run", fake_run)
    path, err = api.ensure_clone("paste-to-skill")
    assert err is None
    assert path == dest.resolve()
    assert path.is_dir()
    assert not dest.is_symlink()
    assert target.is_dir()
    assert (target / "index.html").is_file()


def test_list_apps_readopts_live_vite(isolated, monkeypatch):
    _fake_app(isolated, "paste-to-skill")
    monkeypatch.setattr(
        api,
        "_discover_owned",
        lambda: {
            "paste-to-skill": [
                {"name": "paste-to-skill", "pid": 50, "port": 5241, "pgid": 50},
            ]
        },
    )
    monkeypatch.setattr(api, "_port_open", lambda port: port == 5241)
    monkeypatch.setattr(api, "_proc_alive", lambda pid: pid == 50)
    body = _body(api.list_apps())
    rec = next(a for a in body["apps"] if a["name"] == "paste-to-skill")
    assert rec["cloned"] is True
    assert rec["dev_url"] == "http://127.0.0.1:5241/"
    assert api._PROCS["paste-to-skill"]["pid"] == 50


def test_start_and_stop_go_through_hydrate(isolated, monkeypatch):
    _fake_app(isolated, "skill-lint")
    api._PROCS["skill-lint"] = {"port": 5267, "pid": 77, "pgid": 77}
    monkeypatch.setattr(api, "_port_open", lambda port: port == 5267)
    monkeypatch.setattr(api, "_proc_alive", lambda pid: pid == 77)
    monkeypatch.setattr(api, "ensure_npm_install", lambda _path: None)
    monkeypatch.setattr(
        api.subprocess,
        "Popen",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("second vite")),
    )
    started = _body(api.start_app("skill-lint"))
    assert started["ok"] is True
    assert started["url"] == "http://127.0.0.1:5267/"

    killed = []
    monkeypatch.setattr(
        api,
        "_kill_pg",
        lambda pgid, pid, wait_sec=2.0: killed.append((pgid, pid)),
    )
    stopped = _body(api.stop_app("skill-lint"))
    assert stopped["ok"] is True
    assert "skill-lint" not in api._PROCS
    assert killed == [(77, 77)]
