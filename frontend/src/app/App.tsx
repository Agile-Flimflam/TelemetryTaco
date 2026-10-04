import { useState } from 'react'
import { Suspense, lazy } from 'react'
import { LiveEventStreamCard } from '@/features/events/components/live-event-stream-card'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { PersonView } from '@/features/persons/components/person-view'

const InsightChartCard = lazy(async () => {
  const module = await import('@/features/insights/components/insight-chart-card')
  return { default: module.InsightChartCard }
})

function InsightCardFallback() {
  return (
    <Card className="border-border/70 bg-card/80 shadow-[0_24px_80px_-48px_rgba(0,0,0,0.85)]">
      <CardHeader>
        <CardTitle>Event insights</CardTitle>
        <CardDescription>Loading the analytics surface.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex h-[320px] items-center justify-center rounded-2xl border border-dashed border-border/70 bg-muted/20 text-sm text-muted-foreground">
          Preparing chart module...
        </div>
      </CardContent>
    </Card>
  )
}

function App() {
  const [selectedPerson, setSelectedPerson] = useState<string | null>(null)

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,_rgba(255,140,57,0.25),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(255,214,99,0.18),_transparent_24%),linear-gradient(180deg,_rgba(12,14,18,0.94),_rgba(12,14,18,1))]" />
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-8 px-6 py-10 lg:px-10">
        <header className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px] lg:items-end">
          <div className="space-y-4">
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">Single-project MVP</Badge>
              <Badge variant="outline">Additive API compatibility</Badge>
              <Badge variant="outline">OpenAPI typed frontend</Badge>
            </div>
            <div className="space-y-3">
              <p className="text-sm uppercase tracking-[0.35em] text-muted-foreground">TelemetryTaco</p>
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
                Lightweight telemetry with a clearer ingestion path and a faster dashboard loop.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-muted-foreground">
                Recent events and minute-level insights share one contract surface now, so the UI stays
                thin while the backend handles batching, idempotency, and retention.
              </p>
            </div>
          </div>
          <Card className="border-border/70 bg-card/70 backdrop-blur">
            <CardHeader>
              <CardDescription>Current scope</CardDescription>
              <CardTitle>Strong MVP posture</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-3 text-sm text-muted-foreground">
              <div className="flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-muted/20 px-4 py-3">
                <span>Capture</span>
                <span className="font-medium text-foreground">Single + batch</span>
              </div>
              <div className="flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-muted/20 px-4 py-3">
                <span>Frontend</span>
                <span className="font-medium text-foreground">React Query polling</span>
              </div>
              <div className="flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-muted/20 px-4 py-3">
                <span>SDK</span>
                <span className="font-medium text-foreground">Queued batch sender</span>
              </div>
            </CardContent>
          </Card>
        </header>

        <main className="grid gap-6">
          {selectedPerson ? (
            <PersonView distinctId={selectedPerson} onClose={() => setSelectedPerson(null)} />
          ) : (
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
              <Suspense fallback={<InsightCardFallback />}>
                <InsightChartCard lookbackMinutes={60} />
              </Suspense>
              <LiveEventStreamCard limit={100} onSelectPerson={setSelectedPerson} />
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default App
