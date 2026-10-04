import { useQuery } from '@tanstack/react-query'
import { apiFetch, ApiError } from '@/shared/api/client'
import type { EventRecord, PersonSummary } from '@/shared/api/types'

export const personSummaryQueryKey = ['personSummary'] as const
export const personEventsQueryKey = ['personEvents'] as const

async function fetchPersonSummary(distinctId: string) {
  try {
    return await apiFetch<PersonSummary>(`/api/persons/${distinctId}`)
  } catch (error) {
    if (error instanceof ApiError) {
      throw new Error(`Failed to fetch person summary (HTTP ${error.status}).`)
    }
    throw error
  }
}

async function fetchPersonEvents(distinctId: string, limit: number) {
  try {
    return await apiFetch<EventRecord[]>(`/api/persons/${distinctId}/events?limit=${limit}`)
  } catch (error) {
    if (error instanceof ApiError) {
      throw new Error(`Failed to fetch person events (HTTP ${error.status}).`)
    }
    throw error
  }
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
    refetchInterval: 5000,
  })
}
