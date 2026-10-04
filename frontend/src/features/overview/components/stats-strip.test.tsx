import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { StatsStrip } from '@/features/overview/components/stats-strip'
import { renderWithProviders } from '@/test/test-utils'

function mockJsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('StatsStrip', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders event counts and when the last event arrived', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      mockJsonResponse({
        events_last_24h: 1234,
        unique_distinct_ids_last_24h: 56,
        last_event_received_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
      }),
    )

    renderWithProviders(<StatsStrip />)

    expect(await screen.findByText('1,234')).toBeInTheDocument()
    expect(screen.getByText('56')).toBeInTheDocument()
    expect(screen.getByText('5 minutes ago')).toBeInTheDocument()
  })

  it('shows "Never" before any event has been received', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      mockJsonResponse({
        events_last_24h: 0,
        unique_distinct_ids_last_24h: 0,
        last_event_received_at: null,
      }),
    )

    renderWithProviders(<StatsStrip />)

    expect(await screen.findByText('Never')).toBeInTheDocument()
  })
})
