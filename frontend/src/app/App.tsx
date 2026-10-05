import { LiveEventStreamCard } from '@/features/events/components/live-event-stream-card'
import { ApiHealthIndicator } from '@/features/overview/components/api-health-indicator'
import { StatsStrip } from '@/features/overview/components/stats-strip'
import { InsightChartCard } from '@/features/insights/components/insight-chart-card'
import { CardErrorBoundary } from '@/shared/ui/card-error-boundary'

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

        <CardErrorBoundary title="Event summary">
          <StatsStrip />
        </CardErrorBoundary>

        <main className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <CardErrorBoundary title="Event insights">
            <InsightChartCard lookbackMinutes={60} />
          </CardErrorBoundary>
          <CardErrorBoundary title="Live event stream">
            <LiveEventStreamCard limit={100} />
          </CardErrorBoundary>
        </main>
      </div>
    </div>
  )
}

export default App
