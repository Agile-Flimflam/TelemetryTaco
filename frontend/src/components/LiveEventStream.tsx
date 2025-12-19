import { useState } from 'react'
import { useEventStream } from '@/hooks/useEventStream'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export function LiveEventStream() {
  const { events, loading, error } = useEventStream()
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())

  const toggleExpand = (id: number) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const timeString = date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
    const milliseconds = date.getMilliseconds().toString().padStart(3, '0')
    return `${timeString}.${milliseconds}`
  }

  if (error) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle>Live Event Stream</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-destructive">Error: {error.message}</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full bg-[#1F2937] border-gray-700">
      <CardHeader className="border-b border-gray-700">
        <CardTitle className="text-white font-mono">Live Event Stream</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="bg-[#0a0a0a] min-h-[400px] max-h-[600px] overflow-y-auto font-mono text-sm">
          {loading && events.length === 0 ? (
            <div className="p-4 text-gray-400">Loading events...</div>
          ) : events.length === 0 ? (
            <div className="p-4 text-gray-400">No events yet. Start sending events to see them here.</div>
          ) : (
            <div className="divide-y divide-gray-800">
              {events.map((event) => {
                const isExpanded = expandedIds.has(event.id)
                return (
                  <div
                    key={event.id}
                    className="hover:bg-gray-900 transition-colors cursor-pointer"
                    onClick={() => toggleExpand(event.id)}
                  >
                    <div className="p-3 text-gray-300">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="text-gray-500">
                          [{formatTimestamp(event.timestamp)}]
                        </span>
                        <span className="text-primary font-semibold">
                          {event.event_name}
                        </span>
                        <span className="text-gray-400">|</span>
                        <span className="text-gray-400">{event.distinct_id}</span>
                        <Badge variant="outline" className="ml-auto text-xs">
                          {Object.keys(event.properties).length} props
                        </Badge>
                      </div>
                      {isExpanded && (
                        <div className="mt-3 pt-3 border-t border-gray-800">
                          <div className="text-gray-500 text-xs mb-2">Properties:</div>
                          <pre className="text-gray-400 text-xs overflow-x-auto bg-black/30 p-3 rounded border border-gray-800">
                            {JSON.stringify(event.properties, null, 2)}
                          </pre>
                          <div className="mt-2 text-gray-500 text-xs">
                            UUID: <span className="text-gray-400">{event.uuid}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

