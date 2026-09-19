# SMF App Launcher — agent notes

For Hermes/OpenClaw installing this repo on a user's machine.

## Do

1. Clone to `$HOME/.hermes/plugins/smf-app-launcher` (or `hermes plugins install smfworks/smf-app-launcher --enable`).
2. Run `bash install.sh` from that tree. It enables the plugin on `$HOME/.hermes` **and** every `profiles/*/plugins` home, then copies `desktop/plugin.js` to `$HOME/.hermes/desktop-plugins/smf-app-launcher/`.
3. Tell the user to **quit Hermes Desktop and relaunch from the menu**. The Python API (`plugin_api.py`) mounts only on the next `hermes serve`.

## Do not

- Do not treat ⌘K → Reload desktop plugins as a backend remount. That is JS only. **Backend not reachable** means the serve process predates enable.
- Do not run `hermes desktop` to relaunch if a packaged Electron binary already exists (`…/linux-unpacked/Hermes --no-sandbox`). `hermes desktop` rewrites the `.desktop` `Exec=` and can prompt for `chrome-sandbox` sudo.
- Do not `hermes serve --stop` (kills every serve on the box). Do not kill this chat's backend from inside the same Desktop window unless the user asked for a relaunch.
- Do not iframe Vercel. Start uses `~/.hermes/smf-apps/<kit>` only (never `~/Projects`) and an owned loopback port. Stop via `POST /apps/{name}/stop`.
- Do not `git reset --hard` an existing plugin checkout.

## After relaunch

Sidebar **SMF Apps**, or ⌘K → Open SMF App Launcher. First card click may `git clone` + `npm install`.
