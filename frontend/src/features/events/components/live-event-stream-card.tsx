import { startTransition, useDeferredValue, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useEventsQuery } from '@/features/events/queries'
import { PanelMessage } from '@/shared/ui/panel-message'
import type { EventRecord } from '@/shared/api/types'

interface LiveEventStreamCardProps {
  limit: number
  onSelectPerson?: (distinctId: string) => void
}

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
  onSelectPerson,
}: {
  event: EventRecord
  expanded: boolean
  onToggle: (id: number) => void
  onSelectPerson?: (distinctId: string) => void
}) {
  return (
    <div className="border-b border-border/60 last:border-b-0 hover:bg-muted/30 transition-colors">
      <div className="flex w-full items-center px-4 py-3 text-left">
        <button
          className="flex-1 cursor-pointer"
          onClick={() => onToggle(event.id)}
          type="button"
        >
          <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{event.event_name}</span>
            <span>{formatTimestamp(event.timestamp)}</span>
            <Badge variant="outline">{Object.keys(event.properties).length} props</Badge>
          </div>
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            onSelectPerson?.(event.distinct_id)
          }}
          className="ml-3 text-sm text-muted-foreground hover:text-foreground hover:underline cursor-pointer"
        >
          {event.distinct_id}
        </button>
      </div>
      {expanded ? (
        <div className="px-4 pb-3">
          <div className="mt-1 grid gap-3 rounded-2xl border border-border/70 bg-background/80 p-4">
            <div className="text-xs uppercase tracking-[0.25em] text-muted-foreground">Properties</div>
            <pre className="overflow-x-auto rounded-xl bg-muted/30 p-3 text-xs leading-6 text-foreground">
              {JSON.stringify(event.properties, null, 2)}
            </pre>
            <div className="text-xs text-muted-foreground">
              UUID <span className="font-medium text-foreground">{event.uuid}</span>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export function LiveEventStreamCard({ limit, onSelectPerson }: LiveEventStreamCardProps) {
  const { data = [], error, isLoading } = useEventsQuery(limit)
  const deferredEvents = useDeferredValue(data)
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

  return (
    <Card className="border-border/70 bg-card/80 shadow-[0_24px_80px_-48px_rgba(0,0,0,0.85)]">
      <CardHeader>
        <CardTitle>Live event stream</CardTitle>
        <CardDescription>Polling the last {limit} events every 2 seconds.</CardDescription>
      </CardHeader>
      <CardContent>
        {error ? (
          <PanelMessage
            title="Event stream unavailable"
            description={error.message}
            tone="error"
          />
        ) : isLoading && deferredEvents.length === 0 ? (
          <PanelMessage
            title="Loading events"
            description="Waiting for the first event batch from the API."
          />
        ) : deferredEvents.length === 0 ? (
          <PanelMessage
            title="No events yet"
            description="Send events through the SDK or the capture endpoint to populate this stream."
          />
        ) : (
          <div
            className="max-h-[620px] overflow-y-auto rounded-2xl border border-border/70 bg-background/60"
            style={{ contentVisibility: 'auto' }}
          >
            {deferredEvents.map((event) => (
              <EventRow
                key={event.id}
                event={event}
                expanded={expandedIds.has(event.id)}
                onToggle={toggleExpand}
                onSelectPerson={onSelectPerson}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
