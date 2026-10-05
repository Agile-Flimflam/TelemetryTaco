import { useQuery } from '@tanstack/react-query'
import { apiGet } from '@/shared/api/client'
import { POLL_INTERVAL_MS } from '@/shared/api/polling'

export const statsQueryKey = ['stats'] as const
export const healthQueryKey = ['health'] as const

function fetchStats() {
  return apiGet('/api/stats', { resource: 'stats' })
}

// The readiness endpoint answers 503 with a body when a dependency is down,
// so that body is a valid result rather than an error.
function fetchHealth() {
  return apiGet('/api/health/ready', { resource: 'API health', acceptStatuses: [503] })
}

export function useStatsQuery() {
  return useQuery({
    queryKey: statsQueryKey,
    queryFn: fetchStats,
    refetchInterval: POLL_INTERVAL_MS.stats,
    staleTime: POLL_INTERVAL_MS.stats / 2,
  })
}

export function useHealthQuery() {
  return useQuery({
    queryKey: healthQueryKey,
    queryFn: fetchHealth,
    refetchInterval: POLL_INTERVAL_MS.health,
    staleTime: POLL_INTERVAL_MS.health / 2,
  })
}
