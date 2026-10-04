import { Suspense, lazy } from 'react'
import { LiveEventStreamCard } from '@/features/events/components/live-event-stream-card'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ApiHealthIndicator } from '@/features/overview/components/api-health-indicator'
import { StatsStrip } from '@/features/overview/components/stats-strip'

const InsightChartCard = lazy(async () => {
  const module = await import('@/features/insights/components/insight-chart-card')
  return { default: module.InsightChartCard }
})

function InsightCardFallback() {
  return (
    <Card className="border-border/70 bg-card/80 shadow-[0_24px_80px_-48px_rgba(0,0,0,0.85)]">
      <CardHeader>
        <CardTitle>Event insights</CardTitle>
        <CardDescription>Loading the chart.</CardDescription>
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
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,_rgba(255,140,57,0.25),_transparent_28%),radial-gradient(circle_at_top_right,_rgba(255,214,99,0.18),_transparent_24%),linear-gradient(180deg,_rgba(12,14,18,0.94),_rgba(12,14,18,1))]" />
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-6 px-6 py-8 lg:px-10">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <img src="/favicon.svg" alt="" className="h-10 w-10" />
            <div>
              <h1 className="text-xl font-semibold tracking-tight">TelemetryTaco</h1>
              <p className="text-sm text-muted-foreground">Live product events, self-hosted.</p>
            </div>
          </div>
          <ApiHealthIndicator />
        </header>

        <StatsStrip />

        <main className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <Suspense fallback={<InsightCardFallback />}>
            <InsightChartCard lookbackMinutes={60} />
          </Suspense>
          <LiveEventStreamCard limit={100} />
        </main>
      </div>
    </div>
  )
}

export default App
