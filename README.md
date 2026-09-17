# SMF App Launcher — Hermes Desktop Plugin

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) desktop plugin that scans your local filesystem for installed SMF Works web apps and renders them inside the Hermes desktop workspace — one click, no browser tab needed.

## What it does

- **Sidebar nav** — "SMF Apps" appears below Artifacts in the Hermes Desktop sidebar
- **Local scan only** — scans `~/` and `~/workspace/` for cloned SMF app repos. No GitHub API, no remote listing. Only apps physically on disk appear.
- **Grid view** — cards showing app name, install path, and status badge (installed/running)
- **Live iframe** — clicking "Open" starts a local static file server and renders the app full-pane inside Hermes Desktop
- **Search** — filter installed apps by name
- **⌘K command** — "Open SMF App Launcher" jumps to the apps page

## Install

```bash
# Copy the plugin into your Hermes desktop-plugins directory
mkdir -p ~/.hermes/desktop-plugins/smf-app-launcher
cp plugin/plugin.js ~/.hermes/desktop-plugins/smf-app-launcher/plugin.js
```

Then in Hermes Desktop: **⌘K → "Reload desktop plugins"**

The "SMF Apps" nav row appears in the sidebar. Or use ⌘K → "Open SMF App Launcher".

## How apps are discovered

The plugin scans for directories matching known SMF web app names (with optional `-demo` suffix) that contain an `index.html` file. It checks:

- `~/<app-name>/` and `~/<app-name>-demo/`
- `~/workspace/<app-name>/` and `~/workspace/<app-name>-demo/`

### Currently discovers

Any of these cloned to disk will appear:

| App | Repo |
|-----|------|
| Paste → Skill | [paste-to-skill](https://github.com/smfworks/paste-to-skill) |
| Skill Lint | [skill-lint](https://github.com/smfworks/skill-lint) |
| Skill Card | [skill-card](https://github.com/smfworks/skill-card) |
| Prompt Diff | [prompt-diff](https://github.com/smfworks/prompt-diff) |
| Refuse Card | [refuse-card](https://github.com/smfworks/refuse-card) |
| Tool Permit | [tool-permit](https://github.com/smfworks/tool-permit) |
| Agent Receipt | [agent-receipt](https://github.com/smfworks/agent-receipt) |
| Redact Before Share | [redact-before-share](https://github.com/smfworks/redact-before-share) |
| H3 Longform Capture | [h3-longform-capture](https://github.com/smfworks/h3-longform-capture) |
| Flybrain Visual Demos | [flybrain-visual-demos](https://github.com/smfworks/flybrain-visual-demos) |
| Spark Observatory | [spark-observatory](https://github.com/smfworks/spark-observatory) |
| Hermes Mission Control | [hermes-mission-control](https://github.com/smfworks/hermes-mission-control) |
| Hermes Skill Forge | [hermes-skill-forge](https://github.com/smfworks/hermes-skill-forge) |
| WisdomForge | [wisdomforge](https://github.com/smfworks/wisdomforge) |

### Add a new app

1. Clone the repo: `git clone https://github.com/smfworks/new-app.git ~/new-app`
2. Add the repo name to `KNOWN_APPS` in `plugin/plugin.js`
3. Hit **Refresh** in the launcher (or ⌘K → Reload desktop plugins)

## How it works

When you click "Open" on an app:

1. The plugin spawns a local static file server (`python3 -m http.server`) serving the app's directory
2. The app renders in a sandboxed `<iframe>` filling the workspace pane
3. A back button returns to the grid

No data leaves your machine. All apps run locally.

## Requirements

- [Hermes Desktop](https://github.com/NousResearch/hermes-agent) (the plugin loads in the desktop app, not CLI/gateway alone)
- Python 3 (for the local static file server) or `npx serve` as fallback
- SMF web apps cloned to disk

## License

MIT — SMF Works