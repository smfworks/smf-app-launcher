"""SMF App Launcher — list and start viral SMF tools on this machine.

Membership is the viral kit. Missing clones are installed on Start into
~/.hermes/smf-apps/ only — never npm-install or run a checkout under
~/Projects (or anywhere else).

A local URL is only reported for a Vite process this launcher started (or
re-adopted from that clone root after a Desktop relaunch). Never treat an
unrelated :5173 (or Vercel) as the app.
"""
from __future__ import annotations

import atexit
import json
import os
import re
import shutil
import signal
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

OWNER = "smfworks"
README_URL = f"https://raw.githubusercontent.com/{OWNER}/{OWNER}/main/README.md"
VIRAL_HEADING = "## Try these (viral apps)"
SITE_NAMES = {
    "smfworks", "wisdomforge", "phoenixprotocolml", "hermes-ai-team",
    "smfwisdomforge", "aiclearinghouse-site",
}
REMOTE_RE = re.compile(r"github\.com[:/]+smfworks/([^/\s]+?)(?:\.git)?$", re.I)
KIT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
VITE_PORT_RE = re.compile(rb"--port(?:\s+|=)(\d+)")
NODE_VER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
README_TTL_SEC = 600.0

KIT: Dict[str, Dict[str, str]] = {
    "paste-to-skill": {
        "title": "Paste → Skill",
        "description": "Paste an SOP or notes → Hermes/OpenClaw SKILL.md",
    },
    "skill-lint": {
        "title": "Skill Lint",
        "description": "Green / yellow / red SKILL.md report card with fix hints",
    },
    "skill-card": {
        "title": "Skill Card",
        "description": "Paste a SKILL.md → pretty shareable one-pager PNG",
    },
    "persona-card": {
        "title": "Persona Card",
        "description": "Paste a SOUL / system prompt → shareable agent persona one-pager",
    },
    "prompt-diff": {
        "title": "Prompt Diff",
        "description": "Paste two prompts → visual shareable diff",
    },
    "agent-contract": {
        "title": "Agent Contract",
        "description": "Human↔agent agreement card: roles, success criteria, stop conditions",
    },
    "refuse-card": {
        "title": "Refuse Card",
        "description": "GO / HOLD / NO stamp for a proposed agent action",
    },
    "tool-permit": {
        "title": "Tool Permit",
        "description": "Declare allowed tools → shareable allowlist / PERMIT badge",
    },
    "agent-receipt": {
        "title": "Agent Receipt",
        "description": "Turn any agent session into a dark shareable receipt card",
    },
    "session-timeline": {
        "title": "Session Timeline",
        "description": "Paste an agent/chat log → clean shareable vertical timeline card",
    },
    "handoff-slip": {
        "title": "Handoff Slip",
        "description": "From / to / goal / done / risks / next → shareable agent-to-agent baton slip",
    },
    "redact-before-share": {
        "title": "Redact Before Share",
        "description": "Paste a transcript → scrub secrets/PII → clean export",
    },
    "context-budget": {
        "title": "Context Budget",
        "description": "Paste a prompt or dump → shareable token-budget card",
    },
    "constraint-card": {
        "title": "Constraint Card",
        "description": "Paste must / must-not / stop rules → shareable agent constitution card",
    },
}

_PROCS: Dict[str, Dict[str, Any]] = {}
_PROCS_LOCK = threading.Lock()
_START_LOCKS: Dict[str, threading.Lock] = {}
_START_LOCKS_GUARD = threading.Lock()
_README_CACHE: Optional[Tuple[float, Dict[str, Dict[str, str]]]] = None


def _home() -> Path:
    return Path.home()


def _clone_root() -> Path:
    return _home() / ".hermes" / "smf-apps"


def _state_path() -> Path:
    return _clone_root() / ".state.json"


def _log_dir() -> Path:
    path = _clone_root() / ".logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _is_under_clone_root(path: Path) -> bool:
    try:
        path.resolve().relative_to(_clone_root().resolve())
    except (OSError, ValueError):
        return False
    return True


def _is_site_name(name: str) -> bool:
    n = name.lower()
    if n.endswith("-site") or n.endswith("-website"):
        return True
    return n in SITE_NAMES


def safe_kit_name(name: str) -> Optional[str]:
    n = (name or "").strip().lower()
    if not KIT_NAME_RE.fullmatch(n):
        return None
    if _is_site_name(n):
        return None
    if n not in KIT:
        return None
    return n


def _is_viral_web_app(path: Path) -> bool:
    if not (path / "index.html").is_file():
        return False
    if any((path / n).exists() for n in ("next.config.js", "next.config.ts", "next.config.mjs")):
        return False
    return any((path / n).exists() for n in ("vite.config.ts", "vite.config.js", "vite.config.mjs"))


def _origin_name(path: Path) -> Optional[str]:
    if not (path / ".git").exists():
        return None
    try:
        url = subprocess.check_output(
            ["git", "-C", str(path), "remote", "get-url", "origin"],
            text=True, stderr=subprocess.DEVNULL, timeout=2,
        ).strip()
    except Exception:
        return None
    m = REMOTE_RE.search(url.replace("\\", "/"))
    if not m:
        return None
    return m.group(1).removesuffix(".git")


def _pkg_field(path: Path, key: str) -> str:
    pkg = path / "package.json"
    if not pkg.is_file():
        return ""
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
        return str(data.get(key) or "").strip()
    except Exception:
        return ""


def _port_open(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _proc_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _proc_cmdline(pid: int) -> bytes:
    try:
        return Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return b""


def _proc_cwd(pid: int) -> Optional[Path]:
    try:
        return Path(os.readlink(f"/proc/{pid}/cwd"))
    except OSError:
        return None


def _proc_pgid(pid: int) -> int:
    try:
        return os.getpgid(pid)
    except OSError:
        return pid


def _app_lock(name: str) -> threading.Lock:
    with _START_LOCKS_GUARD:
        lock = _START_LOCKS.get(name)
        if lock is None:
            lock = threading.Lock()
            _START_LOCKS[name] = lock
        return lock


def _load_state() -> Dict[str, Dict[str, Any]]:
    try:
        data = json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for key, rec in data.items():
        if key not in KIT or not isinstance(rec, dict):
            continue
        try:
            out[key] = {
                "port": int(rec["port"]),
                "pid": int(rec.get("pid") or 0),
                "pgid": int(rec.get("pgid") or rec.get("pid") or 0),
            }
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _save_state(procs: Dict[str, Dict[str, Any]]) -> None:
    path = _state_path()
    payload = {
        name: {
            "port": int(rec["port"]),
            "pid": int(rec.get("pid") or 0),
            "pgid": int(rec.get("pgid") or rec.get("pid") or 0),
        }
        for name, rec in procs.items()
        if name in KIT
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def _kill_pg(pgid: int, pid: int, wait_sec: float = 2.0) -> None:
    if pid <= 1:
        return
    if pgid <= 1:
        pgid = pid
    try:
        os.killpg(pgid, signal.SIGTERM)
    except (OSError, AttributeError):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return
    deadline = time.time() + wait_sec
    while time.time() < deadline:
        if not _proc_alive(pid):
            return
        time.sleep(0.05)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except (OSError, AttributeError):
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def _owned_vite_rec(pid: int) -> Optional[Dict[str, Any]]:
    cmd = _proc_cmdline(pid)
    if b"--host" not in cmd or b"127.0.0.1" not in cmd:
        return None
    if b"vite" not in cmd and b"npm" not in cmd:
        return None
    m = VITE_PORT_RE.search(cmd)
    if not m:
        return None
    cwd = _proc_cwd(pid)
    if cwd is None or not _is_under_clone_root(cwd):
        return None
    name = cwd.resolve().name.lower()
    if name not in KIT:
        return None
    return {
        "name": name,
        "pid": pid,
        "port": int(m.group(1)),
        "pgid": _proc_pgid(pid),
    }


def _discover_owned() -> Dict[str, List[Dict[str, Any]]]:
    found: Dict[str, List[Dict[str, Any]]] = {}
    proc_dir = Path("/proc")
    if not proc_dir.is_dir():
        return found
    try:
        entries = list(proc_dir.iterdir())
    except OSError:
        return found
    for entry in entries:
        if not entry.name.isdigit():
            continue
        rec = _owned_vite_rec(int(entry.name))
        if rec:
            found.setdefault(rec["name"], []).append(rec)
    return found


def _prefer_listener(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    for rec in candidates:
        cmd = _proc_cmdline(int(rec["pid"]))
        if b"vite" in cmd:
            return rec
    return min(candidates, key=lambda r: int(r["port"]))


def _adopt_from_state(name: str, rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Trust a persisted pid only if cmdline/cwd still look like our Vite."""
    try:
        pid = int(rec.get("pid") or 0)
        port = int(rec.get("port") or 0)
    except (TypeError, ValueError):
        return None
    if pid <= 1 or not port:
        return None
    owned = _owned_vite_rec(pid)
    if owned is None or owned.get("name") != name:
        return None
    if int(owned["port"]) != port:
        return None
    if not _port_open(port):
        return None
    return {
        "name": name,
        "pid": pid,
        "port": port,
        "pgid": int(owned.get("pgid") or rec.get("pgid") or pid),
    }


def _hydrate_procs() -> None:
    """Re-adopt vites under the clone root; reap duplicate copies of the same app."""
    extras_to_kill: List[Tuple[int, int]] = []
    with _PROCS_LOCK:
        state = {**_load_state(), **dict(_PROCS)}
        live = _discover_owned()
        names = set(KIT) & (set(state) | set(live))
        new_procs: Dict[str, Dict[str, Any]] = {}
        for name in names:
            candidates = list(live.get(name) or [])
            preferred_port = int(state[name]["port"]) if name in state else 0
            keep: Optional[Dict[str, Any]] = None
            if preferred_port:
                keep = next((c for c in candidates if int(c["port"]) == preferred_port), None)
            if keep is None and candidates:
                keep = _prefer_listener(candidates)
            if keep is None and name in state:
                keep = _adopt_from_state(name, state[name])
            if keep is None:
                continue
            new_procs[name] = {
                "port": int(keep["port"]),
                "pid": int(keep["pid"]),
                "pgid": int(keep.get("pgid") or keep["pid"]),
            }
            keep_pid = int(keep["pid"])
            keep_pgid = int(keep.get("pgid") or keep_pid)
            for extra in candidates:
                extra_pid = int(extra["pid"])
                extra_pgid = int(extra.get("pgid") or extra_pid)
                if extra_pid == keep_pid or extra_pgid == keep_pgid:
                    continue
                extras_to_kill.append((extra_pgid, extra_pid))
        _PROCS.clear()
        _PROCS.update(new_procs)
        _save_state(_PROCS)
    for pgid, pid in extras_to_kill:
        _kill_pg(pgid, pid)


def _dev_url(path: Path) -> Optional[str]:
    """Only a server this launcher started for this clone. Never a stray :5173."""
    name = path.name.lower()
    existing = _PROCS.get(name)
    if not existing:
        return None
    port = int(existing["port"])
    pid = int(existing.get("pid") or 0)
    if pid and not _proc_alive(pid):
        with _PROCS_LOCK:
            current = _PROCS.get(name)
            if current and int(current.get("pid") or 0) == pid:
                _PROCS.pop(name, None)
        return None
    if _port_open(port):
        return f"http://127.0.0.1:{port}/"
    return None


def _scan_clones() -> Dict[str, Dict[str, Any]]:
    found: Dict[str, Dict[str, Any]] = {}
    root = _clone_root()
    if not root.is_dir():
        return found
    try:
        kids = list(root.iterdir())
    except OSError:
        return found
    for child in kids:
        if not child.is_dir() or child.name.startswith("."):
            continue
        name = child.name.lower()
        if name not in KIT or not _is_viral_web_app(child):
            continue
        if not _is_under_clone_root(child):
            continue
        origin = _origin_name(child)
        if origin and origin.lower() != name:
            continue
        found[name] = {
            "name": name,
            "title": name,
            "description": _pkg_field(child, "description"),
            "homepage": _pkg_field(child, "homepage").rstrip("/"),
            "vercel_url": "",
            "htmlUrl": f"https://github.com/{OWNER}/{name}",
            "local_path": str(child.resolve()),
            "dev_url": _dev_url(child),
            "has_git": (child / ".git").exists(),
            "cloned": True,
        }
    return found


def parse_viral_readme(md: str) -> Dict[str, Dict[str, str]]:
    extra: Dict[str, Dict[str, str]] = {}
    if not md:
        return extra
    start = md.find(VIRAL_HEADING)
    if start < 0:
        return extra
    rest = md[start + len(VIRAL_HEADING) :]
    nxt = re.search(r"\n## ", rest)
    section = rest[: nxt.start()] if nxt else rest
    for line in section.splitlines():
        if not line.startswith("|") or re.match(r"^\|\s*-+", line):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 2:
            continue
        joined = " ".join(cells)
        gh = re.search(r"https?://github\.com/[^/\s)]+/([^/\s)#]+)", joined, re.I)
        name = gh.group(1).rstrip(").,") if gh else ""
        if not name:
            continue
        title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cells[0]).replace("**", "").strip()
        description = (
            re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cells[1]).replace("**", "").strip()
            if len(cells) > 1 else ""
        )
        extra[name.lower()] = {
            "title": title or name,
            "description": description,
            "vercel_url": "",
        }
    return extra


def _download_readme_extra() -> Dict[str, Dict[str, str]]:
    try:
        req = urllib.request.Request(README_URL, headers={"User-Agent": "smf-app-launcher"})
        with urllib.request.urlopen(req, timeout=8) as res:
            md = res.read().decode("utf-8", errors="replace")
        return parse_viral_readme(md)
    except Exception:
        return {}


def fetch_readme_extra() -> Dict[str, Dict[str, str]]:
    global _README_CACHE
    now = time.monotonic()
    cached = _README_CACHE
    if cached and (now - cached[0]) < README_TTL_SEC:
        return cached[1]
    extra = _download_readme_extra()
    if extra:
        _README_CACHE = (now, extra)
        return extra
    if cached:
        return cached[1]
    return {}


def merge_catalog(
    found: Dict[str, Dict[str, Any]],
    extra: Dict[str, Dict[str, str]],
) -> List[Dict[str, Any]]:
    allowed = set(KIT)
    apps: List[Dict[str, Any]] = []
    for key in allowed:
        rec = dict(found.get(key) or {
            "name": key,
            "title": key,
            "description": "",
            "homepage": "",
            "vercel_url": "",
            "htmlUrl": f"https://github.com/{OWNER}/{key}",
            "local_path": "",
            "dev_url": None,
            "has_git": False,
            "cloned": False,
        })
        rec["name"] = rec.get("name") or key
        rec["cloned"] = bool(rec.get("local_path"))
        rec["vercel_url"] = ""
        meta = {**KIT.get(key, {}), **extra.get(key, {})}
        if meta.get("title"):
            rec["title"] = meta["title"]
        if meta.get("description") and not rec.get("description"):
            rec["description"] = meta["description"]
        rec["htmlUrl"] = rec.get("htmlUrl") or f"https://github.com/{OWNER}/{key}"
        apps.append(rec)
    apps.sort(key=lambda a: (a.get("title") or a["name"]).lower())
    return apps


def _ok(payload: Dict[str, Any], status: int = 200) -> JSONResponse:
    return JSONResponse(payload, status_code=status)


def _fail(error: str, **extra: Any) -> JSONResponse:
    return JSONResponse({"ok": False, "error": error, **extra}, status_code=200)


def _running_payload(kit: str, path: Path, port: int) -> Dict[str, Any]:
    url = f"http://127.0.0.1:{port}/"
    return {
        "ok": True,
        "name": kit,
        "title": KIT.get(kit, {}).get("title") or kit,
        "local_path": str(path),
        "url": url,
        "dev_url": url,
        "vercel_url": "",
        "cloned": True,
    }


@router.get("/apps")
def list_apps() -> JSONResponse:
    _hydrate_procs()
    found = _scan_clones()
    extra = fetch_readme_extra()
    apps = merge_catalog(found, extra)
    return JSONResponse({"apps": apps, "count": len(apps), "source": "smf-apps"})


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "plugin": "smf-app-launcher"}


def _node_version_key(path: Path) -> Tuple[int, int, int]:
    for part in path.parts:
        m = NODE_VER_RE.fullmatch(part)
        if m:
            return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return (0, 0, 0)


def _npm() -> str:
    found = shutil.which("npm")
    if found:
        return found
    nvm = _home() / ".nvm" / "versions" / "node"
    if nvm.is_dir():
        matches = [p for p in nvm.glob("*/bin/npm") if p.is_file()]
        if matches:
            matches.sort(key=_node_version_key, reverse=True)
            return str(matches[0])
    raise FileNotFoundError("npm is not on PATH — install Node.js 20+")


def _node_env() -> Dict[str, str]:
    env = os.environ.copy()
    npm = Path(_npm())
    env["PATH"] = str(npm.parent) + os.pathsep + env.get("PATH", "")
    env["BROWSER"] = "none"
    return env


def ensure_npm_install(path: Path) -> Optional[str]:
    if (path / "node_modules").is_dir():
        return None
    try:
        proc = subprocess.run(
            [_npm(), "install"],
            cwd=str(path),
            env=_node_env(),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except FileNotFoundError as exc:
        return str(exc)
    except subprocess.TimeoutExpired:
        return "npm install timed out after 180s"
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip()[-800:]
        return f"npm install failed: {tail or 'no output'}"
    if not (path / "node_modules").is_dir():
        return "npm install finished but node_modules is still missing"
    return None


def _rm_incomplete(path: Path) -> None:
    if not _is_under_clone_root(path):
        return
    if path.is_symlink() or path.is_file():
        try:
            path.unlink()
        except OSError:
            pass
        return
    if path.exists() and not _is_viral_web_app(path):
        shutil.rmtree(path, ignore_errors=True)


def ensure_clone(name: str) -> Tuple[Optional[Path], Optional[str]]:
    dest = _clone_root() / name
    if dest.is_symlink() and not _is_under_clone_root(dest):
        try:
            dest.unlink()
        except OSError as exc:
            return None, f"could not replace symlink {dest}: {exc}"
    if dest.exists():
        if not _is_under_clone_root(dest):
            return None, f"{dest} is outside ~/.hermes/smf-apps"
        if _is_viral_web_app(dest):
            return dest.resolve(), None
        _rm_incomplete(dest)
        if dest.exists():
            return None, f"{dest} exists but is not a Vite kit app"
    _clone_root().mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/{OWNER}/{name}.git"
    try:
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(dest)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except FileNotFoundError:
        _rm_incomplete(dest)
        return None, "git is not on PATH"
    except subprocess.TimeoutExpired:
        _rm_incomplete(dest)
        return None, "git clone timed out"
    if proc.returncode != 0:
        _rm_incomplete(dest)
        tail = (proc.stderr or proc.stdout or "").strip()[-800:]
        return None, f"git clone failed: {tail or 'no output'}"
    if not _is_under_clone_root(dest) or not _is_viral_web_app(dest):
        _rm_incomplete(dest)
        return None, f"cloned {name} but it is not a Vite client app"
    return dest.resolve(), None


def _pick_port(name: str) -> int:
    owned = {int(rec["port"]) for rec in _PROCS.values() if rec.get("port") is not None}
    base = 5200 + (sum(ord(c) for c in name) % 80)
    for port in range(base, base + 30):
        existing = _PROCS.get(name)
        if existing and int(existing["port"]) == port and _port_open(port):
            return port
        if port not in owned and not _port_open(port):
            return port
    raise RuntimeError(f"no free loopback port in {base}-{base + 29}")


def _tail(path: Path, n: int = 40) -> str:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(lines[-n:]).strip()


def _stop_kit(kit: str) -> None:
    rec = _PROCS.get(kit)
    if rec:
        pid = int(rec.get("pid") or 0)
        pgid = int(rec.get("pgid") or pid)
        _kill_pg(pgid, pid)
    for extra in _discover_owned().get(kit, []):
        _kill_pg(int(extra.get("pgid") or extra["pid"]), int(extra["pid"]))
    with _PROCS_LOCK:
        _PROCS.pop(kit, None)
        _save_state(_PROCS)


@router.post("/apps/{name}/start")
def start_app(name: str) -> JSONResponse:
    """Clone if needed, npm install if needed, start Vite on 127.0.0.1. Never Vercel."""
    kit = safe_kit_name(name)
    if kit is None:
        return _fail("not a viral-kit app")
    with _app_lock(kit):
        return _start_app_locked(kit)


def _start_app_locked(kit: str) -> JSONResponse:
    _hydrate_procs()
    path, clone_err = ensure_clone(kit)
    if clone_err or path is None:
        return _fail(clone_err or "clone failed")

    install_err = ensure_npm_install(path)
    if install_err:
        return _fail(install_err, local_path=str(path))

    existing = _PROCS.get(kit)
    if existing and _port_open(int(existing["port"])) and (
        not existing.get("pid") or _proc_alive(int(existing["pid"]))
    ):
        return _ok(_running_payload(kit, path, int(existing["port"])))

    try:
        port = _pick_port(kit)
    except RuntimeError as exc:
        return _fail(str(exc), local_path=str(path))

    try:
        log_path = _log_dir() / f"{kit}.log"
        log_fh = open(log_path, "ab", buffering=0)
    except OSError as exc:
        return _fail(f"could not write launcher log: {exc}", local_path=str(path))
    try:
        proc = subprocess.Popen(
            [_npm(), "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
            cwd=str(path),
            env=_node_env(),
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    except Exception as exc:
        log_fh.close()
        return _fail(f"could not spawn vite: {exc}", local_path=str(path))
    log_fh.close()

    pgid = proc.pid
    try:
        pgid = os.getpgid(proc.pid)
    except OSError:
        pass

    deadline = time.time() + 40
    while time.time() < deadline:
        if proc.poll() is not None:
            return _fail(
                f"vite exited before bind\n{_tail(log_path)}",
                local_path=str(path),
            )
        if _port_open(port):
            with _PROCS_LOCK:
                _PROCS[kit] = {"port": port, "pid": proc.pid, "pgid": pgid}
                _save_state(_PROCS)
            return _ok(_running_payload(kit, path, port))
        time.sleep(0.3)
    _kill_pg(pgid, proc.pid)
    return _fail(
        f"vite did not bind in time — see {log_path}\n{_tail(log_path)}",
        local_path=str(path),
    )


@router.post("/apps/{name}/stop")
def stop_app(name: str) -> JSONResponse:
    kit = safe_kit_name(name)
    if kit is None:
        return _fail("not a viral-kit app")
    with _app_lock(kit):
        _hydrate_procs()
        _stop_kit(kit)
        return _ok({"ok": True, "name": kit, "stopped": True, "url": "", "dev_url": None})


def _stop_all_tracked() -> None:
    with _PROCS_LOCK:
        items = list(_PROCS.items())
    for name, rec in items:
        pid = int(rec.get("pid") or 0)
        if pid <= 1:
            continue
        cwd = _proc_cwd(pid)
        if cwd is None or not _is_under_clone_root(cwd):
            continue
        _kill_pg(int(rec.get("pgid") or pid), pid)


atexit.register(_stop_all_tracked)
