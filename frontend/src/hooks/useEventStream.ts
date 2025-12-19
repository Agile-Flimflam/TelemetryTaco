import { useState, useEffect } from 'react'

interface EventProperties {
  [key: string]: unknown
}

export interface Event {
  id: number
  distinct_id: string
  event_name: string
  properties: EventProperties
  timestamp: string
  uuid: string
  created_at: string
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export function useEventStream() {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/events`)
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        const data = await response.json()
        setEvents(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err : new Error('Failed to fetch events'))
      } finally {
        setLoading(false)
      }
    }

    // Initial fetch
    fetchEvents()

    // Poll every 2 seconds
    const intervalId = window.setInterval(fetchEvents, 2000)

    return () => {
      clearInterval(intervalId)
    }
  }, [])

  return { events, loading, error }
}

