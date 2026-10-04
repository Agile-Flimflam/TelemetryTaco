import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { ApiHealthIndicator } from '@/features/overview/components/api-health-indicator'
import { renderWithProviders } from '@/test/test-utils'

function mockJsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('ApiHealthIndicator', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('reports a healthy API', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      mockJsonResponse({ status: 'ok', database: 'ok', cache: 'ok' }),
    )

    renderWithProviders(<ApiHealthIndicator />)

    expect(await screen.findByText('API healthy')).toBeInTheDocument()
  })

  it('names the failing dependency when readiness returns 503', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      mockJsonResponse({ status: 'degraded', database: 'ok', cache: 'error' }, 503),
    )

    renderWithProviders(<ApiHealthIndicator />)

    expect(await screen.findByText('API degraded (cache)')).toBeInTheDocument()
  })

  it('reports an unreachable API when the request fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.reject(new TypeError('Failed to fetch')),
    )

    renderWithProviders(<ApiHealthIndicator />)

    expect(await screen.findByText('API unreachable')).toBeInTheDocument()
  })
})
