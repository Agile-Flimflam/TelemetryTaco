// Every viewer polls these endpoints, and the backend rate-limits per client IP. The production
// defaults live in backend/telemetry_taco/settings/base.py, and polling.test.ts fails if an
// interval here would use more than half of one, so a second open tab still fits.
export const POLL_INTERVAL_MS = {
  events: 2_000,
  insights: 30_000,
  stats: 30_000,
  health: 30_000,
} as const
