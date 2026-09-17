# SMF App Launcher — Hermes Desktop Plugin

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) desktop plugin that lists SMF Works viral utility apps **cloned locally on your machine** and renders them inside the Hermes desktop workspace — one click, no browser tab needed.

## What it does

- **Sidebar nav** — "SMF Apps" (rocket icon) appears below Artifacts in the Hermes Desktop sidebar
- **Local disk scan** — the Python backend scans `~/projects/` for cloned SMF app repos. Only apps physically on disk appear. No GitHub API, no remote listing, no marketing sites.
- **Grid view** — cards showing app title, description, source badge (Local dev / Vercel), and git status
- **Live iframe** — clicking "Open" renders the app in a sandboxed iframe filling the workspace pane. Falls back to the Vercel URL if no local dev server is running.
- **Search** — filter installed apps by name or description
- **⌘K command** — "SMF Apps: Open App Launcher" jumps to the apps page

## Install

### Option A: Unified package (recommended)

```bash
git clone https://github.com/smfworks/smf-app-launcher.git ~/.hermes/plugins/smf-app-launcher
```

Then enable the plugin:

```bash
hermes plugins enable smf-app-launcher
```

The Electron main process copies `desktop/plugin.js` into `~/.hermes/desktop-plugins/smf-app-launcher/` automatically. The Python backend (`dashboard/plugin_api.py`) mounts at `/api/plugins/smf-app-launcher/`.

### Option B: Desktop-only (no backend)

```bash
mkdir -p ~/.hermes/desktop-plugins/smf-app-launcher
cp desktop/plugin.js ~/.hermes/desktop-plugins/smf-app-launcher/plugin.js
```

Note: without the Python backend, `ctx.rest('/apps')` will fail and the page shows an error state. The unified package is the intended install path.

### Activate

1. **Settings → Plugins → SMF Apps** → toggle on
2. **⌘K → Reload desktop plugins**
3. Sidebar → **SMF Apps**, or ⌘K → "SMF Apps: Open App Launcher"

## How apps are discovered

The Python backend (`dashboard/plugin_api.py`) has a registry of the 9 SMF viral utility apps. On page load, it scans `~/projects/` for directories matching those names. An app appears **only when its repo is cloned locally**.

### Currently discovers

| App | What it does | Repo |
|-----|-------------|------|
| Redact Before Share | Scrub secrets/PII from transcripts | [redact-before-share](https://github.com/smfworks/redact-before-share) |
| Tool Permit | Agent tool allowlist badge | [tool-permit](https://github.com/smfworks/tool-permit) |
| Prompt Diff | Visual prompt diff | [prompt-diff](https://github.com/smfworks/prompt-diff) |
| Skill Card | SKILL.md → shareable PNG card | [skill-card](https://github.com/smfworks/skill-card) |
| Skill Lint | Lint SKILL.md score card | [skill-lint](https://github.com/smfworks/skill-lint) |
| Refuse Card | GO/HOLD/NO action stamp | [refuse-card](https://github.com/smfworks/refuse-card) |
| Paste to Skill | SOP → clean SKILL.md | [paste-to-skill](https://github.com/smfworks/paste-to-skill) |
| Agent Receipt | Session → shareable receipt card | [agent-receipt](https://github.com/smfworks/agent-receipt) |
| Trajectory Arena | Agentic coding visualizer | [trajectory-arena](https://github.com/smfworks/trajectory-arena) |

**Not included:** marketing sites, infrastructure repos, or anything that isn't a viral utility app.

### Add a new viral app

1. Add an entry to `VIRAL_APPS` in `dashboard/plugin_api.py`
2. Clone the repo: `git clone https://github.com/smfworks/new-app.git ~/projects/new-app`
3. Reload desktop plugins (⌘K → Reload)

## Architecture

```
smf-app-launcher/
├── plugin.yaml              # Agent plugin manifest (kind: standalone)
├── __init__.py              # register(ctx): pass — no agent tools
├── dashboard/
│   ├── manifest.json        # Dashboard/desktop backend mount config
│   └── plugin_api.py        # Python backend — scans ~/projects/, returns app list
├── desktop/
│   └── plugin.js            # Desktop UI — sidebar nav, route, grid + iframe
└── plugin/
    └── plugin.js            # Standalone copy (same file)
```

**Data flow:**

1. Desktop plugin calls `ctx.rest('/apps')` → hits `plugin_api.py` on the gateway
2. Backend scans `~/projects/` for cloned repos in the `VIRAL_APPS` registry
3. Returns JSON `{ apps: [...], projects_dir: "..." }`
4. Desktop renders the grid; clicking "Open" loads the app URL in an iframe

No data leaves your machine. The scan is local. Apps render in a sandboxed iframe with `allow-scripts allow-same-origin allow-forms allow-popups`.

## Requirements

- [Hermes Desktop](https://github.com/NousResearch/hermes-agent) (the plugin loads in the desktop app, not CLI/gateway alone)
- Python 3 (for the backend API — already present with Hermes)
- SMF viral apps cloned to `~/projects/`

## License

MIT — SMF Works