import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/shared/api/client'
import { POLL_INTERVAL_MS } from '@/shared/api/polling'

export const insightsQueryKey = ['insights'] as const

function fetchInsights(lookbackMinutes: number) {
  return apiGet('/api/insights', {
    query: { lookback_minutes: lookbackMinutes },
    resource: 'insights',
  })
}

export function useInsightsQuery(lookbackMinutes: number) {
  return useQuery({
    queryKey: [...insightsQueryKey, lookbackMinutes],
    queryFn: () => fetchInsights(lookbackMinutes),
    refetchInterval: POLL_INTERVAL_MS.insights,
    staleTime: POLL_INTERVAL_MS.insights / 2,
  })
}
