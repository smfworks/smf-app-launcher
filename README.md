# SMF App Launcher

A [Hermes Desktop](https://github.com/NousResearch/hermes-agent) plugin. It lists **SMF viral tools cloned on this machine** and opens them **locally** in the workspace.

It is not a gallery of live Vercel demos, and it does not list company sites.

**License:** MIT

## What it is

- Sidebar row **SMF Apps** (below Artifacts) plus ⌘K → **Open SMF App Launcher**
- Grid of apps that are actually on disk
- **Start local** runs that clone’s Vite dev server on `127.0.0.1` and iframes it
- Search / rescan

## What it is not

- Not the eight public Vercel URLs on [github.com/smfworks](https://github.com/smfworks) (those stay in the browser)
- Not Next.js marketing repos (`*-site`, smfworks.com, WisdomForge, Clearinghouse, …)

## What counts as an app

A directory appears only when all of these hold:

1. Git remote is `github.com/smfworks/<name>`
2. It looks like a Vite client tool (`index.html` + `vite.config.*`)
3. It is in the org README section **Try these (viral apps)** — the eight-tool kit

Clone a kit repo anywhere under `$HOME` (typical: `~/projects/<name>` or `~/projects/<name>-demo`). Rescan. It shows. Until it is cloned, it stays hidden.

## Install

Two halves: a Python scanner the gateway loads, and a Desktop UI file.

```bash
git clone https://github.com/smfworks/smf-app-launcher.git
PLUGIN_SRC=./smf-app-launcher

# Gateway / scanner
mkdir -p ~/.hermes/plugins
rsync -a --exclude '.git' --exclude '__pycache__' "$PLUGIN_SRC/" ~/.hermes/plugins/smf-app-launcher/

# Desktop UI
mkdir -p ~/.hermes/desktop-plugins/smf-app-launcher
cp "$PLUGIN_SRC/desktop/plugin.js" ~/.hermes/desktop-plugins/smf-app-launcher/plugin.js
```

Enable the plugin in `~/.hermes/config.yaml`:

```yaml
plugins:
  enabled:
    - smf-app-launcher
```

Then in Hermes Desktop: **⌘K → Reload desktop plugins**. If the page is empty after that, reload the gateway from a shell outside the running process so `dashboard/plugin_api.py` is imported, then reload plugins again.

On first **Start local**, the clone needs `node_modules` (`npm install` in that app’s directory).

## Layout

```
plugin.yaml                 Hermes plugin metadata
plugin.py                   Agent half (no tools)
dashboard/plugin_api.py     Local clone scanner + Vite starter
dashboard/manifest.json
desktop/plugin.js           Hermes Desktop UI (sidebar, grid, iframe)
```

## Requirements

- Hermes Desktop (the UI file does not load in CLI-only)
- Gateway with this plugin in `plugins.enabled`
- Node.js / npm for **Start local**
- At least one viral-kit repo cloned

## License

MIT — Copyright (c) 2026 SMF Works
