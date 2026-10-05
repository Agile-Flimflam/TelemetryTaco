# frontend/AGENTS.md

React 18 + Vite + TypeScript dashboard. Read the root [`AGENTS.md`](../AGENTS.md) first.

## Layout

```
frontend/src/
├── main.tsx                 # entry; wraps @/app/App in AppProviders
├── app/                     # app shell: App.tsx, providers.tsx, query-client.ts
├── features/<feature>/      # one folder per product area (events, insights, overview)
│   ├── queries.ts           # React Query hooks + fetchers for this feature
│   └── components/          # feature components and their *.test.tsx files
├── shared/
│   ├── api/
│   │   ├── client.ts        # apiGet + ApiError; the only place that calls fetch()
│   │   ├── generated.ts     # GENERATED from openapi.json; never edit by hand
│   │   └── types.ts         # friendly aliases over generated types
│   └── ui/                  # shared components (PanelMessage, CardErrorBoundary)
│       └── primitives/      # shadcn/ui primitives (button, card, badge, table)
├── lib/utils.ts             # cn() class-name helper
└── test/                    # setup.ts + renderWithProviders
```

## Where code goes

- **New product area:** create `features/<name>/` with its own `queries.ts` and `components/`. Features don't import from each other. Move anything shared into `shared/`.
- **API calls:** a fetcher in the feature's `queries.ts` that calls `apiGet` from `@/shared/api/client`, wrapped in a `useQuery` hook. `apiGet` takes a path from the OpenAPI schema and type-checks its query and path params and its response, and it turns network and HTTP failures into readable error messages. Components never call `fetch` directly.
- **API types:** import from `@/shared/api/types`. If a type is missing there, add an alias over `components['schemas'][...]` from `generated.ts`. Don't redeclare backend shapes by hand.
- **UI primitives:** use the shadcn components in `shared/ui/primitives/` before writing new ones. To add one, use the shadcn CLI (`pnpm dlx shadcn@latest add <component>`), which respects `components.json`.
- **App-specific shared UI** goes in `shared/ui/`.

## API types workflow

`openapi.json` and `src/shared/api/generated.ts` are produced from the backend:

```bash
pnpm generate:api-types   # from the repo root: exports schema, then runs openapi-typescript
```

CI regenerates both files and fails on any diff. If the backend changed, regenerate and commit both files in the same PR.

## Conventions

- TypeScript `strict`. `any` is a lint error. Model UI states explicitly (error, loading, empty, data), as `LiveEventStreamCard` and `InsightChartCard` do.
- Styling is Tailwind utility classes plus the CSS variables in `src/index.css` (`hsl(var(--primary))` etc.). Use `cn()` to merge classes, and avoid hard-coded colors when a theme token exists. The look is a dark UI with amber/orange accents.
- Import with `@/…`, never with deep `../../`.
- File names are kebab-case (`live-event-stream-card.tsx`). Component names are PascalCase, and hooks are `useXxxQuery`.
- Polling intervals live in `src/shared/api/polling.ts`, and the query hooks read them from there. Each viewer's polls count against the backend's per-IP rate limits (a 10 s interval is 360 requests per hour), so `polling.test.ts` checks every interval against the production defaults in `backend/config/settings/base.py`.
- Heavy dependencies (Recharts) are lazy-loaded. Keep them out of the initial bundle.
- Every async view needs a visible error state. Use `PanelMessage` with `tone="error"`.
- Each dashboard card is wrapped in `CardErrorBoundary` in `app/App.tsx`, so a render bug in one card doesn't blank the page. Wrap new cards the same way.

## Testing

```bash
pnpm test                                  # all (vitest run)
pnpm vitest run src/features/insights      # one folder
pnpm test:watch
pnpm test:coverage                         # as CI runs it
```

- Put tests next to the component as `*.test.tsx`.
- Render with `renderWithProviders` from `@/test/test-utils`. It gives each test a fresh QueryClient with retries off.
- Mock the network with `vi.spyOn(globalThis, 'fetch')` returning a `Response`, and restore it in `afterEach`.
- Query by visible text or role, not by class names.

## Checks before pushing

```bash
pnpm lint && pnpm type-check && pnpm test && pnpm build
```

## Dev server

`pnpm dev` serves on :5173 and proxies `/api` to `http://localhost:8000`. Set `VITE_API_URL` only when the API is on another origin.

## Environment variables

Vite reads `VITE_*` variables from `frontend/.env`, `frontend/.env.local` and `frontend/.env.[mode]`, never from `backend/.env`. They are baked into the bundle at build time, so they are public. Never put secrets in them.

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | empty (same origin, via the dev proxy) | Base URL of the backend API when it's served from a different origin |
