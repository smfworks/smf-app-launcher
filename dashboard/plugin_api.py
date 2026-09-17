"""SMF App Launcher — list viral SMF tools cloned on this machine.

Membership:
  1. Git remote is github.com/smfworks/<name>
  2. Looks like a Vite client tool (index.html + vite.config), not Next.js sites
  3. Name is not a marketing/site repo

The org README ``## Try these (viral apps)`` section is optional enrichment
(title/description/demo URL). Disk is the source of truth.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

OWNER = "smfworks"
README_URL = f"https://raw.githubusercontent.com/{OWNER}/{OWNER}/main/README.md"
VIRAL_HEADING = "## Try these (viral apps)"
SKIP_DIR = {
    ".git", "node_modules", ".cache", ".venv", "venv", "__pycache__",
    ".npm", ".local", "ComfyUI", "Library", ".hermes",
}
SITE_NAMES = {
    "smfworks", "wisdomforge", "phoenixprotocolml", "hermes-ai-team",
    "smfwisdomforge", "aiclearinghouse-site",
}
REMOTE_RE = re.compile(r"github\.com[:/]+smfworks/([^/\s]+?)(?:\.git)?$", re.I)
MAX_DEPTH = 4


def _home() -> Path:
    return Path.home()


def _is_site_name(name: str) -> bool:
    n = name.lower()
    if n.endswith("-site") or n.endswith("-website"):
        return True
    return n in SITE_NAMES


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

    sock = socket.socket()
    sock.settimeout(0.15)
    try:
        sock.connect(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _dev_url(path: Path) -> Optional[str]:
    pkg = path / "package.json"
    ports: List[int] = []
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            script = str(data.get("scripts", {}).get("dev", ""))
        except Exception:
            script = ""
        match = re.search(r"--port\s+(\d+)", script)
        if match:
            ports.append(int(match.group(1)))
    ports.extend([5173, 4173, 3000])
    seen = set()
    for port in ports:
        if port in seen:
            continue
        seen.add(port)
        if _port_open(port):
            return f"http://127.0.0.1:{port}"
    return None


def _rank(path: Path) -> int:
    s = str(path)
    if path.name.endswith("-demo"):
        return 0
    if "/projects/" in s:
        return 5
    if "/workspace/" in s:
        return 15
    if "oversight-cache" in s:
        return 90
    return 10


def _walk(root: Path, depth: int, found: Dict[str, Dict[str, Any]]) -> None:
    if depth > MAX_DEPTH or not root.is_dir():
        return
    name = _origin_name(root)
    if name and not _is_site_name(name) and _is_viral_web_app(root):
        rec = {
            "name": name,
            "title": name,
            "description": _pkg_field(root, "description"),
            "homepage": _pkg_field(root, "homepage").rstrip("/"),
            "vercel_url": "",
            "htmlUrl": f"https://github.com/{OWNER}/{name}",
            "local_path": str(root.resolve()),
            "dev_url": _dev_url(root),
            "has_git": True,
        }
        home = rec["homepage"]
        if home.startswith("http") and (".vercel.app" in home or ".netlify.app" in home):
            rec["vercel_url"] = home if home.endswith("/") else home + "/"
        prev = found.get(name.lower())
        if prev is None or _rank(root) < _rank(Path(prev["local_path"])):
            found[name.lower()] = rec
        return
    try:
        kids = list(root.iterdir())
    except OSError:
        return
    for child in kids:
        if not child.is_dir() or child.name in SKIP_DIR or child.name.startswith("."):
            continue
        _walk(child, depth + 1, found)


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
        demo = re.search(r"https?://[^\s)<>\"]+\.(?:vercel|netlify)\.app[^\s)<>\"]*", joined, re.I)
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
            "vercel_url": (demo.group(0).rstrip(".,;") + "/") if demo else "",
        }
    return extra


def fetch_readme_extra() -> Dict[str, Dict[str, str]]:
    try:
        req = urllib.request.Request(README_URL, headers={"User-Agent": "smf-app-launcher"})
        with urllib.request.urlopen(req, timeout=8) as res:
            md = res.read().decode("utf-8", errors="replace")
        return parse_viral_readme(md)
    except Exception:
        return {}


@router.get("/apps")
async def list_apps() -> JSONResponse:
    found: Dict[str, Dict[str, Any]] = {}
    home = _home()
    bases = (
        home / "projects",
        home / "workspace",
        home / "src",
        home / "github",
        home / "smf-apps",
        home / ".hermes" / "smf-apps",
        home / "smf-oversight-cache" / "repos",
        home / "Documents",
        home / "prod-hardening",
        home / "Downloads",
    )
    for base in bases:
        if base.is_dir():
            _walk(base, 0, found)
    try:
        for child in home.iterdir():
            if not child.is_dir() or child.name.startswith(".") or child.name in SKIP_DIR:
                continue
            _walk(child, MAX_DEPTH, found)
    except OSError:
        pass
    extra = fetch_readme_extra()
    apps = []
    for key, rec in found.items():
        if extra and key not in extra:
            continue
        meta = extra.get(key, {})
        if meta.get("title"):
            rec["title"] = meta["title"]
        if meta.get("description") and not rec.get("description"):
            rec["description"] = meta["description"]
        if meta.get("vercel_url") and not rec.get("vercel_url"):
            rec["vercel_url"] = meta["vercel_url"]
        apps.append(rec)
    apps.sort(key=lambda a: (a.get("title") or a["name"]).lower())
    return JSONResponse({"apps": apps, "count": len(apps), "source": "local-clone"})


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "plugin": "smf-app-launcher"}


_PROCS: Dict[str, Dict[str, Any]] = {}


def _port_open(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


@router.post("/apps/{name}/start")
def start_app(name: str) -> JSONResponse:
    """Start the local Vite dev server for a cloned kit app. Never opens Vercel."""
    import socket
    import time

    found: Dict[str, Dict[str, Any]] = {}
    home = _home()
    for base in (
        home / ".hermes" / "smf-apps",
        home / "projects",
        home / "workspace",
        home / "smf-oversight-cache" / "repos",
        home / "src",
    ):
        if base.is_dir():
            _walk(base, 0, found)
    rec = found.get(name.lower())
    if rec is None:
        return JSONResponse({"ok": False, "error": "not cloned on this machine"}, status_code=404)
    extra = fetch_readme_extra()
    if extra and name.lower() not in extra:
        return JSONResponse({"ok": False, "error": "not a viral-kit app"}, status_code=404)
    path = Path(rec["local_path"])
    if not (path / "node_modules").is_dir():
        return JSONResponse(
            {
                "ok": False,
                "error": "cloned but node_modules is missing — run npm install in " + str(path),
                "local_path": str(path),
            },
            status_code=409,
        )
    existing = _PROCS.get(name.lower())
    if existing and _port_open(int(existing["port"])):
        rec["url"] = f"http://127.0.0.1:{existing['port']}/"
        rec["dev_url"] = rec["url"]
        rec["vercel_url"] = ""
        return JSONResponse({"ok": True, **rec})
    port = 5200 + (sum(ord(c) for c in name.lower()) % 80)
    env = os.environ.copy()
    env["BROWSER"] = "none"
    proc = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port), "--strictPort"],
        cwd=str(path),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    deadline = time.time() + 25
    while time.time() < deadline:
        if proc.poll() is not None:
            return JSONResponse({"ok": False, "error": "vite exited before bind"}, status_code=500)
        if _port_open(port):
            _PROCS[name.lower()] = {"port": port, "pid": proc.pid}
            rec["url"] = f"http://127.0.0.1:{port}/"
            rec["dev_url"] = rec["url"]
            rec["vercel_url"] = ""
            return JSONResponse({"ok": True, **rec})
        time.sleep(0.3)
    return JSONResponse({"ok": False, "error": "vite did not bind in time"}, status_code=504)
