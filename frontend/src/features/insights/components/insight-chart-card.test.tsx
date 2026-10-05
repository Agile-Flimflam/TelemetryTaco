import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { InsightChartCard } from '@/features/insights/components/insight-chart-card'
import { renderWithProviders } from '@/test/test-utils'

function mockJsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('InsightChartCard', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders an empty-state message', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => mockJsonResponse([]))

    renderWithProviders(<InsightChartCard lookbackMinutes={60} />)

    expect(await screen.findByText('No data available')).toBeInTheDocument()
  })

  it('treats a zero-filled series as empty', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      mockJsonResponse([
        { bucket: '2026-10-04T12:29:00Z', time: '12:29', count: 0 },
        { bucket: '2026-10-04T12:30:00Z', time: '12:30', count: 0 },
      ]),
    )

    renderWithProviders(<InsightChartCard lookbackMinutes={2} />)

    expect(await screen.findByText('No data available')).toBeInTheDocument()
  })

  it('renders an error message on request failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(new Response('oops', { status: 500 })),
    )

    renderWithProviders(<InsightChartCard lookbackMinutes={60} />)

    expect(await screen.findByText('Insight query failed')).toBeInTheDocument()
  })
})
