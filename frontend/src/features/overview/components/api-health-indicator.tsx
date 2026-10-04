import { useHealthQuery } from '@/features/overview/queries'
import { cn } from '@/lib/utils'

type HealthState = 'checking' | 'ok' | 'degraded' | 'unreachable'

const stateStyles: Record<HealthState, { dot: string; label: string }> = {
  checking: { dot: 'bg-muted-foreground', label: 'Checking API' },
  ok: { dot: 'bg-emerald-400', label: 'API healthy' },
  degraded: { dot: 'bg-amber-400', label: 'API degraded' },
  unreachable: { dot: 'bg-destructive', label: 'API unreachable' },
}

export function ApiHealthIndicator() {
  const { data, error, isLoading } = useHealthQuery()

  let state: HealthState = 'checking'
  if (error) {
    state = 'unreachable'
  } else if (!isLoading && data) {
    state = data.status === 'ok' ? 'ok' : 'degraded'
  }

  const failing = data
    ? (['database', 'cache'] as const).filter((dependency) => data[dependency] !== 'ok')
    : []
  const detail = state === 'degraded' && failing.length > 0 ? ` (${failing.join(', ')})` : ''
  const { dot, label } = stateStyles[state]

  return (
    <div
      className="flex items-center gap-2 rounded-full border border-border/70 bg-card/70 px-3 py-1.5 text-xs text-muted-foreground"
      role="status"
    >
      <span className={cn('h-2 w-2 rounded-full', dot)} aria-hidden="true" />
      <span>
        {label}
        {detail}
      </span>
    </div>
  )
}
