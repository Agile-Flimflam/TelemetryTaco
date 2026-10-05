import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatBucketLabel, formatBucketTooltip } from '@/features/insights/format'
import type { InsightPoint } from '@/shared/api/types'

interface InsightLineChartProps {
  data: InsightPoint[]
}

// Above this many points, per-minute dots blur into a solid band.
const MAX_POINTS_WITH_DOTS = 90

export function InsightLineChart({ data }: InsightLineChartProps) {
  const showDots = data.length <= MAX_POINTS_WITH_DOTS

  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="4 4" stroke="hsl(var(--border))" />
        <XAxis
          dataKey="bucket"
          tickFormatter={formatBucketLabel}
          minTickGap={24}
          stroke="hsl(var(--muted-foreground))"
          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="hsl(var(--muted-foreground))"
          tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
          tickLine={false}
          axisLine={false}
          allowDecimals={false}
        />
        <Tooltip
          labelFormatter={(bucket) => formatBucketTooltip(String(bucket))}
          contentStyle={{
            borderRadius: 16,
            border: '1px solid hsl(var(--border))',
            backgroundColor: 'hsl(var(--card))',
            color: 'hsl(var(--foreground))',
          }}
        />
        <Line
          dataKey="count"
          type="monotone"
          stroke="hsl(var(--primary))"
          strokeWidth={3}
          dot={showDots ? { fill: 'hsl(var(--primary))', r: 4 } : false}
          activeDot={{ r: 6 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
