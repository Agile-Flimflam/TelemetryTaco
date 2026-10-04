import type { components } from '@/shared/api/generated'

export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue }

type EventSchema = components['schemas']['EventResponseSchema']

export interface EventRecord extends Omit<EventSchema, 'id' | 'timestamp' | 'properties'> {
  id: number
  timestamp: string
  properties: Record<string, JsonValue>
}

export type InsightPoint = components['schemas']['InsightDataPoint']
export type HealthStatus = components['schemas']['HealthStatusResponse']
export type PersonSummary = components['schemas']['PersonSummaryResponse']
