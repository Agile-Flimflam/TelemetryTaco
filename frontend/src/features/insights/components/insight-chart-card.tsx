import { Suspense, lazy } from 'react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/shared/ui/primitives/card'
import { useInsightsQuery } from '@/features/insights/queries'
import { PanelMessage } from '@/shared/ui/panel-message'

interface InsightChartCardProps {
  lookbackMinutes: number
}

const LazyInsightLineChart = lazy(async () => {
  const module = await import('@/features/insights/components/insight-line-chart')
  return { default: module.InsightLineChart }
})

export function InsightChartCard({ lookbackMinutes }: InsightChartCardProps) {
  const { data = [], error, isLoading } = useInsightsQuery(lookbackMinutes)

  return (
    <Card className="border-border/70 bg-card/80 shadow-[0_24px_80px_-48px_rgba(0,0,0,0.85)]">
      <CardHeader>
        <CardTitle>Event insights</CardTitle>
        <CardDescription>
          Minute-level event counts over the last {lookbackMinutes} minutes.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {error ? (
          <PanelMessage title="Insight query failed" description={error.message} tone="error" />
        ) : isLoading ? (
          <PanelMessage
            title="Loading insight series"
            description="Running the initial aggregation query."
          />
        ) : data.every((point) => point.count === 0) ? (
          <PanelMessage
            title="No data available"
            description="Once events are captured, they will aggregate here by minute."
          />
        ) : (
          <Suspense
            fallback={
              <PanelMessage
                title="Loading chart library"
                description="The data is ready; the chart module is being loaded."
              />
            }
          >
            <LazyInsightLineChart data={data} />
          </Suspense>
        )}
      </CardContent>
    </Card>
  )
}
