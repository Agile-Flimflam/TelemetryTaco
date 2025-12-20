import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface InsightDataPoint {
  time: string
  count: number
}

// Use relative URL in development (Vite proxy) or explicit URL from env
const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'http://localhost:8000')

interface InsightChartProps {
  lookbackMinutes?: number
}

export function InsightChart({ lookbackMinutes = 60 }: InsightChartProps) {
  const [data, setData] = useState<InsightDataPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        setLoading(true)
        const url = `${API_BASE_URL}/api/insights?lookback_minutes=${lookbackMinutes}`
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        const result = await response.json()
        setData(result)
        setError(null)
      } catch (err) {
        const errorMessage = err instanceof Error 
          ? err.message 
          : 'Failed to fetch insights'
        const detailedError = err instanceof TypeError && err.message.includes('fetch')
          ? new Error(`${errorMessage}. Is the backend server running on port 8000?`)
          : new Error(errorMessage)
        setError(detailedError)
      } finally {
        setLoading(false)
      }
    }

    fetchInsights()

    // Refresh every 10 seconds
    const intervalId = setInterval(fetchInsights, 10000)

    return () => {
      clearInterval(intervalId)
    }
  }, [lookbackMinutes])

  // Custom dark mode tooltip
  const CustomTooltip = ({ active, payload, label }: {
    active?: boolean
    payload?: Array<{ value: number; name: string }>
    label?: string
  }) => {
    if (active && payload && payload.length > 0) {
      return (
        <div className="bg-[#1F2937] border border-gray-700 rounded-lg p-3 shadow-lg">
          <p className="text-gray-300 text-sm mb-1">{`Time: ${label}`}</p>
          <p className="text-primary font-semibold text-sm">
            {`Events: ${payload[0].value}`}
          </p>
        </div>
      )
    }
    return null
  }

  if (error) {
    return (
      <Card className="w-full bg-[#1F2937] border-gray-700">
        <CardHeader>
          <CardTitle className="text-white font-mono">Event Insights</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-destructive">Error: {error.message}</div>
        </CardContent>
      </Card>
    )
  }

  if (loading) {
    return (
      <Card className="w-full bg-[#1F2937] border-gray-700">
        <CardHeader>
          <CardTitle className="text-white font-mono">Event Insights</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-gray-400">Loading insights...</div>
        </CardContent>
      </Card>
    )
  }

  if (data.length === 0) {
    return (
      <Card className="w-full bg-[#1F2937] border-gray-700">
        <CardHeader>
          <CardTitle className="text-white font-mono">Event Insights</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center text-gray-400">
            <div className="text-center">
              <p className="mb-2">No data available</p>
              <p className="text-sm text-gray-500">
                Events will appear here once they are captured
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full bg-[#1F2937] border-gray-700">
      <CardHeader>
        <CardTitle className="text-white font-mono">
          Event Insights ({lookbackMinutes} min lookback)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={data}
            margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#404040" />
            <XAxis
              dataKey="time"
              stroke="#9ca3af"
              tick={{ fill: '#9ca3af', fontSize: 12 }}
            />
            <YAxis
              stroke="#9ca3af"
              tick={{ fill: '#9ca3af', fontSize: 12 }}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line
              type="monotone"
              dataKey="count"
              stroke="#f54e00"
              strokeWidth={2}
              dot={{ fill: '#f54e00', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}

