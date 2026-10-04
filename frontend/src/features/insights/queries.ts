import { useQuery } from '@tanstack/react-query'
import { apiFetch, ApiError } from '@/shared/api/client'
import { POLL_INTERVAL_MS } from '@/shared/api/polling'
import type { InsightPoint } from '@/shared/api/types'

export const insightsQueryKey = ['insights'] as const

async function fetchInsights(lookbackMinutes: number) {
  try {
    return await apiFetch<InsightPoint[]>(`/api/insights?lookback_minutes=${lookbackMinutes}`)
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error('Failed to fetch insights. Is the backend server running on port 8000?')
    }

    if (error instanceof ApiError) {
      throw new Error(`Failed to fetch insights (HTTP ${error.status}).`)
    }

    throw error
  }
}

export function useInsightsQuery(lookbackMinutes: number) {
  return useQuery({
    queryKey: [...insightsQueryKey, lookbackMinutes],
    queryFn: () => fetchInsights(lookbackMinutes),
    refetchInterval: POLL_INTERVAL_MS.insights,
    staleTime: POLL_INTERVAL_MS.insights / 2,
  })
}
