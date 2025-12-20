import { useState, useEffect } from 'react'

/**
 * Represents a JSON-serializable value.
 * This type ensures type safety while allowing flexible event properties.
 */
type JsonValue =
  | string
  | number
  | boolean
  | null
  | { [key: string]: JsonValue }
  | JsonValue[]

/**
 * Event properties are a flexible JSON object that can contain
 * any JSON-serializable values (strings, numbers, booleans, null, objects, arrays).
 */
interface EventProperties {
  [key: string]: JsonValue
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

// Use relative URL in development (Vite proxy) or explicit URL from env
const API_BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '' : 'http://localhost:8000')

export function useEventStream() {
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const url = `${API_BASE_URL}/api/events`
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        })
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        const data = await response.json()
        setEvents(data)
        setError(null)
      } catch (err) {
        const errorMessage = err instanceof Error 
          ? err.message 
          : 'Failed to fetch events'
        const detailedError = err instanceof TypeError && err.message.includes('fetch')
          ? new Error(`${errorMessage}. Is the backend server running on port 8000?`)
          : new Error(errorMessage)
        setError(detailedError)
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

