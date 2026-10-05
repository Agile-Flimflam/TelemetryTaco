import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/shared/api/client'
import { POLL_INTERVAL_MS } from '@/shared/api/polling'
import type { EventRecord } from '@/shared/api/types'

export const eventsQueryKey = ['events'] as const

async function fetchEvents(limit: number) {
  const events = await apiGet('/api/events', { query: { limit }, resource: 'events' })
  return events as EventRecord[]
}

export function useEventsQuery(limit: number) {
  return useQuery({
    queryKey: [...eventsQueryKey, limit],
    queryFn: () => fetchEvents(limit),
    refetchInterval: POLL_INTERVAL_MS.events,
    staleTime: POLL_INTERVAL_MS.events / 2,
  })
}
