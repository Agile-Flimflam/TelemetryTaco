import { useQuery } from '@tanstack/react-query'
import { apiFetch, ApiError } from '@/shared/api/client'
import { POLL_INTERVAL_MS } from '@/shared/api/polling'
import type { EventRecord } from '@/shared/api/types'

export const eventsQueryKey = ['events'] as const

async function fetchEvents(limit: number) {
  try {
    return await apiFetch<EventRecord[]>(`/api/events?limit=${limit}`)
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error('Failed to fetch events. Is the backend server running on port 8000?')
    }

    if (error instanceof ApiError) {
      throw new Error(`Failed to fetch events (HTTP ${error.status}).`)
    }

    throw error
  }
}

export function useEventsQuery(limit: number) {
  return useQuery({
    queryKey: [...eventsQueryKey, limit],
    queryFn: () => fetchEvents(limit),
    refetchInterval: POLL_INTERVAL_MS.events,
    staleTime: POLL_INTERVAL_MS.events / 2,
  })
}
