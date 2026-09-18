# SMF App Launcher — Hermes Desktop Plugin

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) desktop plugin that lists the SMF Works viral kit and opens each app **locally** in the workspace. One click clones, installs, and starts Vite on `127.0.0.1`. It does not iframe Vercel.

## What it does

- **Sidebar** — SMF Apps, plus ⌘K → Open SMF App Launcher
- **Kit grid** — the ten viral tools, even before they are cloned
- **Install & open** — clone into `~/.hermes/smf-apps/<app>`, `npm install` if needed, start Vite on a dedicated loopback port, iframe that URL
- **Owned ports only** — never treats an unrelated Vite on `:5173` as the app
- **Not included** — marketing sites, Next.js `*-site` repos, WisdomForge, Clearinghouse, smfworks.com

## Install

```bash
git clone https://github.com/smfworks/smf-app-launcher.git ~/.hermes/plugins/smf-app-launcher
mkdir -p ~/.hermes/desktop-plugins/smf-app-launcher
cp ~/.hermes/plugins/smf-app-launcher/desktop/plugin.js ~/.hermes/desktop-plugins/smf-app-launcher/plugin.js
hermes plugins enable smf-app-launcher
```

Then remount the Desktop backend (quit and relaunch Hermes Desktop, or restart the `hermes serve` process). ⌘K → Reload desktop plugins loads the UI only; it does not mount `plugin_api.py`.

1. Settings → Plugins → SMF Apps → on
2. Sidebar → **SMF Apps**

Needs Node.js 20+ (`npm`) and git on PATH. First open of an app can take a minute while `npm install` runs.

## Viral kit

| App | What it does | Repo |
|-----|-------------|------|
| Paste → Skill | Paste an SOP or notes → Hermes/OpenClaw `SKILL.md` | [paste-to-skill](https://github.com/smfworks/paste-to-skill) |
| Skill Lint | Green / yellow / red `SKILL.md` report card | [skill-lint](https://github.com/smfworks/skill-lint) |
| Skill Card | `SKILL.md` → shareable PNG | [skill-card](https://github.com/smfworks/skill-card) |
| Prompt Diff | Visual shareable prompt diff | [prompt-diff](https://github.com/smfworks/prompt-diff) |
| Agent Contract | Roles, success criteria, stop conditions | [agent-contract](https://github.com/smfworks/agent-contract) |
| Refuse Card | `GO` / `HOLD` / `NO` stamp | [refuse-card](https://github.com/smfworks/refuse-card) |
| Tool Permit | Allowed-tools badge | [tool-permit](https://github.com/smfworks/tool-permit) |
| Agent Receipt | Session → shareable receipt | [agent-receipt](https://github.com/smfworks/agent-receipt) |
| Redact Before Share | Scrub secrets/PII from a transcript | [redact-before-share](https://github.com/smfworks/redact-before-share) |
| Context Budget | Token-budget card | [context-budget](https://github.com/smfworks/context-budget) |

Add a kit name to `KIT` in `dashboard/plugin_api.py`. Titles also enrich from the `smfworks/smfworks` README section `## Try these (viral apps)`.

## Architecture

```
smf-app-launcher/
├── plugin.yaml
├── __init__.py
├── dashboard/
│   ├── manifest.json        # api: plugin_api.py
│   └── plugin_api.py        # GET /apps, POST /apps/{name}/start
├── desktop/
│   └── plugin.js            # copy to ~/.hermes/desktop-plugins/smf-app-launcher/
└── tests/
    └── test_plugin_api.py
```

`POST /apps/{name}/start` returns HTTP 200 with `{ok: true, url}` or `{ok: false, error}`. Desktop `ctx.rest` throws on 4xx, so expected setup failures stay 200.

## Tests

```bash
python -m pytest tests/test_plugin_api.py -q
```

## License

MIT — SMF Works
