import { afterEach, describe, expect, it, vi } from 'vitest'

// The frontend has no Node types, but Vitest runs in Node, where assigning TZ changes the zone.
declare const process: { env: Record<string, string | undefined> }

const originalTimeZone = process.env.TZ

async function formatInTimeZone(timeZone: string, bucket: string) {
  process.env.TZ = timeZone
  vi.resetModules()
  const { formatBucketLabel } = await import('@/features/insights/format')
  return formatBucketLabel(bucket)
}

describe('formatBucketLabel', () => {
  afterEach(() => {
    process.env.TZ = originalTimeZone
    vi.resetModules()
  })

  it('shows UTC buckets in the browser time zone', async () => {
    const bucket = '2026-10-04T12:30:00Z'

    expect(await formatInTimeZone('UTC', bucket)).toMatch(/12:30/)
    expect(await formatInTimeZone('Asia/Kolkata', bucket)).toMatch(/06:00/)
  })
})
