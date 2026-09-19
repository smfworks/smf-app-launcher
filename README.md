# SMF App Launcher — Hermes Desktop Plugin

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) desktop plugin that lists the SMF Works viral kit and opens each app **locally** in the workspace. One click clones, installs, and starts Vite on `127.0.0.1`. It does not iframe Vercel.

## What it does

- **Sidebar** — SMF Apps, plus ⌘K → Open SMF App Launcher
- **Kit grid** — the fourteen viral tools, even before they are cloned
- **Install & open** — clone into `~/.hermes/smf-apps/<app>` only, `npm install` if needed, start Vite on a dedicated loopback port, iframe that URL
- **Stop / open in browser** — Stop kills the owned process group; Open in browser uses the OS handler
- **Owned ports only** — never treats an unrelated Vite on `:5173` as the app; relaunch re-adopts leftover vites under `smf-apps` and reaps duplicates
- **Not included** — marketing sites, Next.js `*-site` repos, WisdomForge, Clearinghouse, smfworks.com

## Install

One shot (covers profiles + Desktop JS + enable):

```bash
git clone https://github.com/smfworks/smf-app-launcher.git ~/.hermes/plugins/smf-app-launcher
bash ~/.hermes/plugins/smf-app-launcher/install.sh
```

Or, if Hermes is already on PATH:

```bash
hermes plugins install smfworks/smf-app-launcher --enable
bash "${HERMES_HOME:-$HOME/.hermes}/plugins/smf-app-launcher/install.sh"
```

`install.sh` enables the plugin on `$HOME/.hermes` **and** every `profiles/*/plugins` home Desktop may spawn, copies `desktop/plugin.js` into `$HOME/.hermes/desktop-plugins/smf-app-launcher/` (what packaged Electron actually loads), and tells you to **quit and relaunch Desktop**.

**⌘K → Reload desktop plugins is JS only.** It does not mount `plugin_api.py`. If SMF Apps says **Backend not reachable**, the serve process started before enable — quit Desktop and launch it again.

Do **not** run `hermes desktop` to relaunch if you already have the packaged Linux binary. That command rewrites the `.desktop` `Exec=` and can prompt for `chrome-sandbox` sudo. Use the menu entry / `…/linux-unpacked/Hermes --no-sandbox`.

Then:

1. Settings → Plugins → SMF Apps → on
2. Sidebar → **SMF Apps** (or ⌘K → Open SMF App Launcher)

Needs Node.js 20+ (`npm`) and git on PATH. First open of an app can take a minute while `npm install` runs.

### Give this to a Hermes agent

```
Install SMF App Launcher from https://github.com/smfworks/smf-app-launcher
Run bash ~/.hermes/plugins/smf-app-launcher/install.sh (clone first if missing).
Enable on $HOME/.hermes and every profiles/*/ that already has a plugins dir.
Copy desktop/plugin.js to $HOME/.hermes/desktop-plugins/smf-app-launcher/.
Do not run hermes desktop. Do not kill this chat from inside it.
Tell me to quit Hermes Desktop and relaunch from the menu so plugin_api.py mounts.
```

## Viral kit

| App | What it does | Repo |
|-----|-------------|------|
| Paste → Skill | Paste an SOP or notes → Hermes/OpenClaw `SKILL.md` | [paste-to-skill](https://github.com/smfworks/paste-to-skill) |
| Skill Lint | Green / yellow / red `SKILL.md` report card | [skill-lint](https://github.com/smfworks/skill-lint) |
| Skill Card | `SKILL.md` → shareable PNG | [skill-card](https://github.com/smfworks/skill-card) |
| Persona Card | SOUL / system prompt → persona one-pager | [persona-card](https://github.com/smfworks/persona-card) |
| Prompt Diff | Visual shareable prompt diff | [prompt-diff](https://github.com/smfworks/prompt-diff) |
| Agent Contract | Roles, success criteria, stop conditions | [agent-contract](https://github.com/smfworks/agent-contract) |
| Refuse Card | `GO` / `HOLD` / `NO` stamp | [refuse-card](https://github.com/smfworks/refuse-card) |
| Tool Permit | Allowed-tools badge | [tool-permit](https://github.com/smfworks/tool-permit) |
| Agent Receipt | Session → shareable receipt | [agent-receipt](https://github.com/smfworks/agent-receipt) |
| Session Timeline | Chat log → vertical timeline card | [session-timeline](https://github.com/smfworks/session-timeline) |
| Handoff Slip | Agent-to-agent baton slip | [handoff-slip](https://github.com/smfworks/handoff-slip) |
| Redact Before Share | Scrub secrets/PII from a transcript | [redact-before-share](https://github.com/smfworks/redact-before-share) |
| Context Budget | Token-budget card | [context-budget](https://github.com/smfworks/context-budget) |
| Constraint Card | Must / must-not / stop rules card | [constraint-card](https://github.com/smfworks/constraint-card) |

Add a kit name to `KIT` in `dashboard/plugin_api.py`. Titles also enrich from the `smfworks/smfworks` README section `## Try these (viral apps)`.

## Architecture

```
smf-app-launcher/
├── install.sh
├── AGENTS.md
├── plugin.yaml
├── __init__.py
├── dashboard/
│   ├── manifest.json        # api: plugin_api.py
│   └── plugin_api.py        # GET /apps, POST /apps/{name}/start|stop
├── desktop/
│   └── plugin.js            # copy to ~/.hermes/desktop-plugins/smf-app-launcher/
└── tests/
    └── test_plugin_api.py
```

`POST /apps/{name}/start` and `POST /apps/{name}/stop` return HTTP 200 with `{ok: true, url}` or `{ok: false, error}`. Desktop `ctx.rest` throws on 4xx, so expected setup failures stay 200. Clones, `npm install`, and Vite always run under `~/.hermes/smf-apps/<app>` — never a `~/Projects` checkout.

## Tests

```bash
python -m pytest tests/test_plugin_api.py -q
```

## License

MIT — SMF Works
