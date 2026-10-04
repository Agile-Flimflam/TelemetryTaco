import { useDeferredValue, useState, startTransition } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PanelMessage } from '@/shared/ui/panel-message'
import { usePersonSummaryQuery, usePersonEventsQuery } from '../queries'
import { Button } from '@/components/ui/button'
import { EventRecord } from '@/shared/api/types'

const timestampFormatter = new Intl.DateTimeFormat('en-US', {
  hour12: false,
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
})

function formatTimestamp(timestamp: string) {
  const date = new Date(timestamp)
  return `${timestampFormatter.format(date)}.${date.getMilliseconds().toString().padStart(3, '0')}`
}
function EventRow({
  event,
  expanded,
  onToggle,
}: {
  event: EventRecord
  expanded: boolean
  onToggle: (id: number) => void
}) {
  return (
    <button
      className="w-full cursor-pointer border-b border-border/60 px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-muted/30"
      onClick={() => onToggle(event.id)}
      type="button"
    >
      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
        <span className="font-medium text-foreground">{event.event_name}</span>
        <span>{formatTimestamp(event.timestamp)}</span>
        <Badge variant="outline">{Object.keys(event.properties).length} props</Badge>
      </div>
      {expanded ? (
        <div className="mt-3 grid gap-3 rounded-2xl border border-border/70 bg-background/80 p-4">
          <div className="text-xs uppercase tracking-[0.25em] text-muted-foreground">Properties</div>
          <pre className="overflow-x-auto rounded-xl bg-muted/30 p-3 text-xs leading-6 text-foreground">
            {JSON.stringify(event.properties, null, 2)}
          </pre>
        </div>
      ) : null}
    </button>
  )
}

interface PersonViewProps {
  distinctId: string
  onClose: () => void
}

export function PersonView({ distinctId, onClose }: PersonViewProps) {
  const { data: summary, isLoading: isLoadingSummary } = usePersonSummaryQuery(distinctId)
  const { data: events = [], isLoading: isLoadingEvents } = usePersonEventsQuery(distinctId, 100)
  const deferredEvents = useDeferredValue(events)
  
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())

  function toggleExpand(id: number) {
    startTransition(() => {
      setExpandedIds((previous) => {
        const next = new Set(previous)
        if (next.has(id)) {
          next.delete(id)
        } else {
          next.add(id)
        }
        return next
      })
    })
  }

  if (isLoadingSummary) {
    return <PanelMessage title="Loading person" description="Fetching summary..." />
  }

  if (!summary) {
    return <PanelMessage title="Error" description="Failed to load person summary." tone="error" />
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-semibold tracking-tight">Person: {distinctId}</h2>
        <Button onClick={onClose} variant="outline">Back to Stream</Button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="py-4">
            <CardDescription>First seen</CardDescription>
            <CardTitle className="text-lg">{summary.first_seen ? new Date(summary.first_seen).toLocaleString() : 'N/A'}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="py-4">
            <CardDescription>Last seen</CardDescription>
            <CardTitle className="text-lg">{summary.last_seen ? new Date(summary.last_seen).toLocaleString() : 'N/A'}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="py-4">
            <CardDescription>Event count</CardDescription>
            <CardTitle className="text-lg">{summary.event_count}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="py-4">
            <CardDescription>Top Events</CardDescription>
            <div className="text-sm mt-2 space-y-1">
              {summary.top_events?.map(e => (
                <div key={e.event_name} className="flex justify-between">
                  <span className="truncate max-w-[100px]">{e.event_name}</span>
                  <span className="text-muted-foreground">{e.count}</span>
                </div>
              ))}
            </div>
          </CardHeader>
        </Card>
      </div>

      <Card className="border-border/70 bg-card/80 shadow-[0_24px_80px_-48px_rgba(0,0,0,0.85)]">
        <CardHeader>
          <CardTitle>Event Timeline</CardTitle>
          <CardDescription>Recent events for {distinctId}</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoadingEvents && deferredEvents.length === 0 ? (
            <PanelMessage title="Loading events" description="Fetching timeline..." />
          ) : deferredEvents.length === 0 ? (
            <PanelMessage title="No events" description="No events found for this person." />
          ) : (
            <div className="max-h-[500px] overflow-y-auto rounded-2xl border border-border/70 bg-background/60">
              {deferredEvents.map((event) => (
                <EventRow
                  key={event.id}
                  event={event}
                  expanded={expandedIds.has(event.id)}
                  onToggle={toggleExpand}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
