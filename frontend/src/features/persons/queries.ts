import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/shared/api/client'
import { POLL_INTERVAL_MS } from '@/shared/api/polling'
import type { EventRecord, PersonSummary } from '@/shared/api/types'

export const personSummaryQueryKey = ['personSummary'] as const
export const personEventsQueryKey = ['personEvents'] as const

async function fetchPersonSummary(distinctId: string) {
  const summary = await apiGet('/api/persons/{distinct_id}', {
    params: { distinct_id: distinctId },
    resource: 'person summary',
  })
  return summary as PersonSummary
}

async function fetchPersonEvents(distinctId: string, limit: number) {
  const events = await apiGet('/api/persons/{distinct_id}/events', {
    params: { distinct_id: distinctId },
    query: { limit },
    resource: 'person events',
  })
  return events as EventRecord[]
}

export function usePersonSummaryQuery(distinctId: string) {
  return useQuery({
    queryKey: [...personSummaryQueryKey, distinctId],
    queryFn: () => fetchPersonSummary(distinctId),
    staleTime: 5000,
  })
}

export function usePersonEventsQuery(distinctId: string, limit: number) {
  return useQuery({
    queryKey: [...personEventsQueryKey, distinctId, limit],
    queryFn: () => fetchPersonEvents(distinctId, limit),
    refetchInterval: POLL_INTERVAL_MS.events,
  })
}
