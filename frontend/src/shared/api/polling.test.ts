import { describe, expect, it } from 'vitest'
import baseSettings from '../../../../backend/telemetry_taco/settings/base.py?raw'
import { POLL_INTERVAL_MS } from '@/shared/api/polling'

const SECONDS_PER_UNIT: Record<string, number> = { s: 1, m: 60, h: 3600, d: 86400 }

function defaultRequestsPerHour(setting: string): number {
  const match = baseSettings.match(
    new RegExp(`${setting} = env\\("${setting}", default="(\\d+)/([smhd])"\\)`),
  )
  if (!match) {
    throw new Error(`Could not find the default for ${setting} in settings/base.py`)
  }

  const [, count, unit] = match
  return (Number(count) * 3600) / SECONDS_PER_UNIT[unit]
}

function pollsPerHour(intervalMs: number): number {
  return 3_600_000 / intervalMs
}

describe('dashboard polling', () => {
  // Health has no rate limit, so it isn't listed.
  it.each([
    ['events', 'RATE_LIMIT_LIST_EVENTS', POLL_INTERVAL_MS.events],
    ['insights', 'RATE_LIMIT_GET_INSIGHTS', POLL_INTERVAL_MS.insights],
    ['stats', 'RATE_LIMIT_GET_INSIGHTS', POLL_INTERVAL_MS.stats],
  ])('keeps %s polling under half of %s', (_name, setting, intervalMs) => {
    expect(pollsPerHour(intervalMs)).toBeLessThanOrEqual(defaultRequestsPerHour(setting) / 2)
  })
})
