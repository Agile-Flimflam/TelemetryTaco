import { useQuery } from '@tanstack/react-query'
import { apiFetch, ApiError, buildApiUrl } from '@/shared/api/client'
import type { EventStats, HealthStatus } from '@/shared/api/types'

export const statsQueryKey = ['stats'] as const
export const healthQueryKey = ['health'] as const

async function fetchStats() {
  try {
    return await apiFetch<EventStats>('/api/stats')
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error('Failed to fetch stats. Is the backend server running on port 8000?')
    }

    if (error instanceof ApiError) {
      throw new Error(`Failed to fetch stats (HTTP ${error.status}).`)
    }

    throw error
  }
}

// The readiness endpoint answers 503 with a body when a dependency is down,
// so read the body for both 200 and 503 instead of going through apiFetch.
async function fetchHealth(): Promise<HealthStatus> {
  const response = await fetch(buildApiUrl('/api/health/ready'))
  if (response.ok || response.status === 503) {
    return (await response.json()) as HealthStatus
  }

  throw new ApiError(`Request failed with status ${response.status}`, response.status)
}

export function useStatsQuery() {
  return useQuery({
    queryKey: statsQueryKey,
    queryFn: fetchStats,
    refetchInterval: 30000,
    staleTime: 15000,
  })
}

export function useHealthQuery() {
  return useQuery({
    queryKey: healthQueryKey,
    queryFn: fetchHealth,
    refetchInterval: 30000,
    staleTime: 15000,
  })
}
