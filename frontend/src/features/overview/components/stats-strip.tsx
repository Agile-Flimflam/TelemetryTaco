import { useStatsQuery } from '@/features/overview/queries'

const numberFormatter = new Intl.NumberFormat('en-US')
const relativeTimeFormatter = new Intl.RelativeTimeFormat('en-US', { numeric: 'auto' })

function formatRelativeTime(timestamp: string, now: number = Date.now()) {
  const seconds = Math.round((new Date(timestamp).getTime() - now) / 1000)
  const absSeconds = Math.abs(seconds)

  if (absSeconds < 60) {
    return relativeTimeFormatter.format(seconds, 'second')
  }
  if (absSeconds < 60 * 60) {
    return relativeTimeFormatter.format(Math.round(seconds / 60), 'minute')
  }
  if (absSeconds < 60 * 60 * 24) {
    return relativeTimeFormatter.format(Math.round(seconds / 3600), 'hour')
  }
  return relativeTimeFormatter.format(Math.round(seconds / 86400), 'day')
}

function StatTile({ label, value, title }: { label: string; value: string; title?: string }) {
  return (
    <div className="rounded-2xl border border-border/70 bg-card/70 px-5 py-4 backdrop-blur">
      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold tracking-tight text-foreground" title={title}>
        {value}
      </p>
    </div>
  )
}

export function StatsStrip() {
  const { data, error } = useStatsQuery()
  const placeholder = error ? 'n/a' : '…'

  const lastEvent = data?.last_event_received_at
  return (
    <section aria-label="Event summary" className="grid gap-4 sm:grid-cols-3">
      <StatTile
        label="Events (24h)"
        value={data ? numberFormatter.format(data.events_last_24h) : placeholder}
      />
      <StatTile
        label="Unique users (24h)"
        value={data ? numberFormatter.format(data.unique_distinct_ids_last_24h) : placeholder}
      />
      <StatTile
        label="Last event received"
        value={data ? (lastEvent ? formatRelativeTime(lastEvent) : 'Never') : placeholder}
        title={lastEvent ? new Date(lastEvent).toLocaleString() : undefined}
      />
    </section>
  )
}
