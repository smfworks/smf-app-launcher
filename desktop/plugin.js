/**
 * SMF App Launcher — local viral kit only.
 * Open starts localhost Vite. Never iframes Vercel or marketing sites.
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

function localUrl(app) {
  if (!app) return ''
  const u = app.url || app.dev_url || ''
  if (typeof u !== 'string') return ''
  if (u.includes('vercel.app') || u.includes('netlify.app')) return ''
  return u
}

function AppCard({ app, onOpen }) {
  const url = localUrl(app)
  const busy = useValue($starting) === app.name
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
            variant: 'secondary',
            className: 'shrink-0 text-[0.625rem]',
            children: url ? 'Local' : 'Cloned',
          }),
        ],
      }),
      jsx('div', {
        className: 'line-clamp-2 text-xs leading-relaxed text-(--ui-text-secondary)',
        children: app.description || app.local_path,
      }),
      jsx(Button, {
        variant: 'default',
        size: 'sm',
        disabled: !app.local_path || busy,
        onClick: () => {
          haptic('tap')
          onOpen(app)
        },
        className: 'h-7 text-xs',
        children: busy ? 'Starting…' : url ? 'Open' : 'Start local',
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
  return jsxs('div', {
    className: 'flex h-full flex-col gap-3 p-4',
    children: [
      jsx(SearchField, {
        value: search,
        placeholder: 'Search cloned viral apps…',
        onChange: (v) => $searchQuery.set(v),
        className: 'h-8',
      }),
      jsx('div', {
        className: 'text-xs text-(--ui-text-tertiary)',
        children: filtered.length + ' viral app' + (filtered.length === 1 ? '' : 's') + ' cloned on this machine',
      }),
      filtered.length === 0
        ? jsx(EmptyState, {
            title: 'No matching apps',
            description: 'Clone a viral SMF app (Vite tool, not a *-site), then Rescan.',
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

function AppLive({ app, onBack }) {
  const url = localUrl(app)
  return jsxs('div', {
    className: 'flex h-full min-h-0 flex-col',
    children: [
      jsxs('div', {
        className: 'flex items-center gap-2 border-b border-(--ui-stroke-secondary) px-3 py-2',
        children: [
          jsx(Button, {
            variant: 'ghost',
            size: 'sm',
            onClick: () => {
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
          jsx(Badge, { variant: 'secondary', className: 'text-[0.625rem]', children: 'localhost' }),
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
            description: 'Cloned, but not running on localhost.',
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
    return jsx(AppLive, { app: selected, onBack: () => $selectedApp.set(null) })
  }
  if (isLoading) {
    return jsxs('div', {
      className: 'flex h-full flex-col items-center justify-center gap-3',
      children: [
        jsx(GlyphSpinner, { size: 24 }),
        jsx('div', { className: 'text-sm text-(--ui-text-secondary)', children: 'Scanning local clones…' }),
      ],
    })
  }
  if (error) {
    return jsx(ErrorState, {
      title: 'Backend not reachable',
      description: 'Enable smf-app-launcher in Settings → Plugins, then reload.',
    })
  }
  if (apps.length === 0) {
    return jsxs('div', {
      className: 'flex h-full flex-col items-center justify-center gap-3 p-8',
      children: [
        jsx(EmptyState, {
          title: 'No viral apps cloned',
          description: 'Clone a kit app from the SMF Works README (Try these — viral apps). Sites are ignored.',
        }),
        jsx(Button, { variant: 'ghost', size: 'sm', onClick: () => refetch(), children: 'Rescan' }),
      ],
    })
  }
  return jsx(AppGrid, {
    apps,
    onOpen: async (app) => {
      const existing = localUrl(app)
      if (existing) {
        $selectedApp.set({ ...app, url: existing })
        return
      }
      $starting.set(app.name)
      try {
        const started = await ctx.rest('/apps/' + encodeURIComponent(app.name) + '/start', { method: 'POST' })
        const local = localUrl(started)
        if (!local) {
          host.notify({ kind: 'error', message: (started && started.error) || 'Local start failed' })
          return
        }
        $selectedApp.set({ ...app, ...started, url: local })
      } catch (err) {
        host.notify({ kind: 'error', message: (err && err.message) || 'Could not start local app' })
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
