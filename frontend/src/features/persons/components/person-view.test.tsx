import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { PersonView } from '@/features/persons/components/person-view'
import { renderWithProviders } from '@/test/test-utils'

const summary = {
  distinct_id: 'alice',
  first_seen: '2026-10-01T10:00:00Z',
  last_seen: '2026-10-02T12:00:00Z',
  event_count: 42,
  top_events: [{ event_name: 'signup', count: 30 }],
}

const personEvent = {
  id: 1,
  uuid: '5bb31741-4f62-4fab-8fc4-45a8ee3a5487',
  distinct_id: 'alice',
  event_name: 'page_view',
  properties: { path: '/' },
  timestamp: '2026-10-02T12:00:00Z',
  created_at: '2026-10-02T12:00:00Z',
}

function mockJsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

function mockPersonEndpoints(eventsBody: unknown) {
  return vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
    const url = String(input)
    if (url.includes('/api/persons/alice/events')) {
      return mockJsonResponse(eventsBody)
    }
    return mockJsonResponse(summary)
  })
}

describe('PersonView', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a loading state while the summary is fetched', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {}))

    renderWithProviders(<PersonView distinctId="alice" onClose={() => {}} />)

    expect(screen.getByText('Loading person')).toBeInTheDocument()
  })

  it('renders the summary and event timeline for the person', async () => {
    mockPersonEndpoints([personEvent])

    renderWithProviders(<PersonView distinctId="alice" onClose={() => {}} />)

    expect(await screen.findByText('Person: alice')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('signup')).toBeInTheDocument()
    expect(await screen.findByText('page_view')).toBeInTheDocument()
  })

  it('shows an empty state when the person has no events', async () => {
    mockPersonEndpoints([])

    renderWithProviders(<PersonView distinctId="alice" onClose={() => {}} />)

    expect(await screen.findByText('Person: alice')).toBeInTheDocument()
    expect(await screen.findByText('No events found for this person.')).toBeInTheDocument()
  })
})
