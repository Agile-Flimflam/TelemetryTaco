import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiGet } from '@/shared/api/client'

function mockJsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('apiGet', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('sends query params and returns the JSON body', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockImplementation(() => mockJsonResponse([]))

    await expect(
      apiGet('/api/events', { query: { limit: 25, before: null }, resource: 'events' }),
    ).resolves.toEqual([])

    expect(fetchSpy).toHaveBeenCalledWith('/api/events?limit=25', expect.anything())
  })

  it('names the resource and status when the API returns an error', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => mockJsonResponse({}, 500))

    const request = apiGet('/api/stats', { resource: 'stats' })

    await expect(request).rejects.toBeInstanceOf(ApiError)
    await expect(request).rejects.toThrow('Failed to fetch stats (HTTP 500).')
  })

  it('explains a network failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.reject(new TypeError('Failed to fetch')),
    )

    await expect(apiGet('/api/stats', { resource: 'stats' })).rejects.toThrow(
      'Failed to fetch stats. Is the backend server running on port 8000?',
    )
  })

  it('returns the body for an accepted non-2xx status', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      mockJsonResponse({ status: 'degraded', database: 'ok', cache: 'error' }, 503),
    )

    await expect(
      apiGet('/api/health/ready', { resource: 'API health', acceptStatuses: [503] }),
    ).resolves.toEqual({ status: 'degraded', database: 'ok', cache: 'error' })
  })

  it('rejects unknown paths and wrong params at compile time', () => {
    // Never called: these lines only need to fail type-checking (`pnpm type-check`).
    const typeChecks = () => {
      // @ts-expect-error: no such endpoint
      void apiGet('/api/nope', { resource: 'nothing' })
      // @ts-expect-error: capture is POST-only
      void apiGet('/api/capture', { resource: 'capture' })
      // @ts-expect-error: insights takes lookback_minutes, not limit
      void apiGet('/api/insights', { query: { limit: 5 }, resource: 'insights' })
      // @ts-expect-error: limit is a number
      void apiGet('/api/events', { query: { limit: '5' }, resource: 'events' })
    }
    expect(typeChecks).toBeTypeOf('function')
  })
})
