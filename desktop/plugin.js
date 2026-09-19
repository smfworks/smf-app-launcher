/**
 * SMF App Launcher — local viral kit only.
 * Open clones + npm install + starts localhost Vite. Never iframes Vercel.
 */
import {
  cn,
  haptic,
  host,
  PALETTE_AREA,
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  Badge,
  Button,
  Codicon,
  EmptyState,
  ErrorState,
  GlyphSpinner,
  ScrollArea,
  SearchField,
  Separator,
  atom,
  useValue,
  useQuery,
} from '@hermes/plugin-sdk'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'smf-app-launcher'
const $selectedApp = atom(null)
const $searchQuery = atom('')
const $starting = atom(null)
const START_TIMEOUT_MS = 420000

function localUrl(app) {
  if (!app) return ''
  const raw = app.url || app.dev_url || ''
  if (typeof raw !== 'string') return ''
  let parsed
  try {
    parsed = new URL(raw)
  } catch {
    return ''
  }
  if (parsed.username || parsed.password) return ''
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return ''
  if (parsed.hostname !== '127.0.0.1' && parsed.hostname !== 'localhost') return ''
  if (parsed.hostname.includes('vercel.app') || parsed.hostname.includes('netlify.app')) return ''
  return parsed.href
}

function errText(err) {
  if (!err) return 'Could not start local app'
  if (typeof err === 'string') return err
  if (err.error) return String(err.error)
  if (err.message) return String(err.message)
  return 'Could not start local app'
}

function statusLabel(app) {
  if (localUrl(app)) return 'Running'
  if (app.local_path) return 'Cloned'
  return 'Not installed'
}

function AppCard({ app, onOpen }) {
  const url = localUrl(app)
  const starting = useValue($starting)
  const thisStarting = starting === app.name
  const busy = thisStarting
  return jsxs('div', {
    className: cn(
      'group relative flex flex-col gap-2 rounded-lg border border-(--ui-stroke-secondary)',
      'p-3 transition-all hover:border-(--ui-accent)'
    ),
    children: [
      jsxs('div', {
        className: 'flex items-center gap-2',
        children: [
          jsx('div', {
            className: 'flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-(--ui-accent)',
            children: jsx(Codicon, { name: 'package', size: 16 }),
          }),
          jsx('div', {
            className: 'min-w-0 flex-1 truncate text-sm font-medium',
            children: app.title || app.name,
          }),
          jsx(Badge, {
            className: 'shrink-0 text-[0.625rem]',
            children: statusLabel(app),
          }),
        ],
      }),
      jsx('div', {
        className: 'line-clamp-2 text-xs leading-relaxed text-(--ui-text-secondary)',
        children: app.description || app.local_path || 'Click to install and open locally.',
      }),
      jsx(Button, {
        variant: 'default',
        size: 'sm',
        disabled: busy,
        onClick: () => {
          haptic('tap')
          onOpen(app)
        },
        className: 'h-7 text-xs',
        children: thisStarting ? 'Starting…' : url ? 'Open' : app.local_path ? 'Start local' : 'Install & open',
      }),
    ],
  })
}

function AppGrid({ apps, onOpen }) {
  const search = useValue($searchQuery)
  const q = search.trim().toLowerCase()
  const filtered = q
    ? apps.filter(
        (a) =>
          String(a.name || '').toLowerCase().includes(q) ||
          String(a.title || '').toLowerCase().includes(q) ||
          String(a.description || '').toLowerCase().includes(q)
      )
    : apps
  const cloned = apps.filter((a) => a.local_path).length
  return jsxs('div', {
    className: 'flex h-full flex-col gap-3 p-4',
    children: [
      jsx(SearchField, {
        value: search,
        placeholder: 'Search viral apps…',
        onChange: (v) => $searchQuery.set(v),
        containerClassName: 'h-8',
      }),
      jsx('div', {
        className: 'text-xs text-(--ui-text-tertiary)',
        children:
          filtered.length +
          ' kit app' +
          (filtered.length === 1 ? '' : 's') +
          ' · ' +
          cloned +
          ' cloned on this machine',
      }),
      filtered.length === 0
        ? jsx(EmptyState, {
            title: 'No matching apps',
            description: 'The viral kit is listed even before clone. Try a different search.',
          })
        : jsx(ScrollArea, {
            className: 'min-h-0 flex-1',
            children: jsx('div', {
              className: 'grid grid-cols-[repeat(auto-fill,minmax(240px,1fr))] gap-2 pb-4',
              children: filtered.map((app) => jsx(AppCard, { app, onOpen }, app.name)),
            }),
          }),
    ],
  })
}

function openLocal(url, ctx) {
  const viaOs = ctx && ctx.os && typeof ctx.os.openExternal === 'function'
  if (viaOs) {
    void ctx.os.openExternal(url)
    return
  }
  if (typeof host.openExternal === 'function') {
    void host.openExternal(url)
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}

function AppLive({ app, ctx, onBack }) {
  const url = localUrl(app)
  const stopping = useValue($starting) === 'stop:' + app.name
  return jsxs('div', {
    className: 'flex h-full min-h-0 flex-col',
    children: [
      jsxs('div', {
        className: 'flex items-center gap-2 border-b border-(--ui-stroke-secondary) px-3 py-2',
        children: [
          jsx(Button, {
            variant: 'ghost',
            size: 'sm',
            disabled: stopping,
            onClick: () => {
              if (stopping) return
              haptic('tap')
              onBack()
            },
            className: 'h-7 text-xs',
            children: 'Back',
          }),
          jsx(Separator, { orientation: 'vertical', className: 'h-4' }),
          jsx('div', {
            className: 'min-w-0 flex-1 truncate text-sm font-medium',
            children: app.title || app.name,
          }),
          jsx(Badge, { className: 'text-[0.625rem]', children: 'localhost' }),
          url
            ? jsx(Button, {
                variant: 'ghost',
                size: 'sm',
                className: 'h-7 text-xs',
                onClick: () => {
                  haptic('tap')
                  openLocal(url, ctx)
                },
                children: 'Open in browser',
              })
            : null,
          jsx(Button, {
            variant: 'ghost',
            size: 'sm',
            disabled: stopping,
            className: 'h-7 text-xs',
            onClick: async () => {
              haptic('tap')
              $starting.set('stop:' + app.name)
              try {
                await ctx.rest('/apps/' + encodeURIComponent(app.name) + '/stop', {
                  method: 'POST',
                })
                onBack()
              } catch (err) {
                host.notify({ kind: 'error', message: errText(err) })
              } finally {
                $starting.set(null)
              }
            },
            children: stopping ? 'Stopping…' : 'Stop',
          }),
        ],
      }),
      url
        ? jsx('iframe', {
            src: url,
            className: 'min-h-0 w-full flex-1 border-0',
            title: app.title || app.name,
            sandbox: 'allow-scripts allow-same-origin allow-forms allow-popups allow-downloads',
            allow: 'clipboard-read; clipboard-write',
          })
        : jsx(EmptyState, {
            title: 'No local server',
            description: 'Start the app to open it on localhost.',
          }),
    ],
  })
}

function AppLauncherPage({ ctx }) {
  const selected = useValue($selectedApp)
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: [ID, 'apps'],
    queryFn: async () => ctx.rest('/apps'),
    staleTime: 30 * 1000,
    retry: 1,
  })
  const apps = (data && data.apps) || []
  if (selected) {
    return jsx(AppLive, {
      app: selected,
      ctx,
      onBack: () => {
        $selectedApp.set(null)
        void refetch()
      },
    })
  }
  if (isLoading) {
    return jsxs('div', {
      className: 'flex h-full flex-col items-center justify-center gap-3',
      children: [
        jsx(GlyphSpinner, { size: 24 }),
        jsx('div', { className: 'text-sm text-(--ui-text-secondary)', children: 'Loading viral kit…' }),
      ],
    })
  }
  if (error) {
    return jsxs('div', {
      className: 'flex h-full flex-col items-center justify-center gap-3 p-8',
      children: [
        jsx(ErrorState, {
          title: 'Backend not reachable',
          description:
            'Enable SMF Apps in Settings → Plugins, then quit Hermes Desktop and relaunch from the menu. Reload desktop plugins is JS only.',
        }),
        jsx(Button, { variant: 'ghost', size: 'sm', onClick: () => refetch(), children: 'Retry' }),
      ],
    })
  }
  if (apps.length === 0) {
    return jsxs('div', {
      className: 'flex h-full flex-col items-center justify-center gap-3 p-8',
      children: [
        jsx(EmptyState, {
          title: 'No viral apps',
          description: 'The kit should list even before clone. Rescan, or remount the plugin backend.',
        }),
        jsx(Button, { variant: 'ghost', size: 'sm', onClick: () => refetch(), children: 'Rescan' }),
      ],
    })
  }
  return jsx(AppGrid, {
    apps,
    onOpen: async (app) => {
      $starting.set(app.name)
      try {
        const started = await ctx.rest('/apps/' + encodeURIComponent(app.name) + '/start', {
          method: 'POST',
          timeoutMs: START_TIMEOUT_MS,
        })
        if (started && started.ok === false) {
          host.notify({ kind: 'error', message: errText(started) })
          return
        }
        const local = localUrl(started)
        if (!local) {
          host.notify({ kind: 'error', message: errText(started) || 'Local start failed' })
          return
        }
        $selectedApp.set({ ...app, ...started, url: local })
        void refetch()
      } catch (err) {
        host.notify({ kind: 'error', message: errText(err) })
      } finally {
        $starting.set(null)
      }
    },
  })
}

export default {
  id: ID,
  name: 'SMF Apps',
  defaultEnabled: true,
  register(ctx) {
    ctx.registerMany([
      {
        id: `${ID}-nav`,
        area: SIDEBAR_NAV_AREA,
        data: { path: '/smf-apps', label: 'SMF Apps', codicon: 'extensions' },
      },
      {
        id: `${ID}-route`,
        area: ROUTES_AREA,
        data: { path: '/smf-apps' },
        render: () => jsx(AppLauncherPage, { ctx }),
      },
      {
        id: `${ID}-palette`,
        area: PALETTE_AREA,
        data: {
          id: `${ID}-open`,
          label: 'Open SMF App Launcher',
          run: () => host.navigate('/smf-apps'),
        },
      },
    ])
  },
}
