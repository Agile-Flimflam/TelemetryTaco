import type { paths } from '@/shared/api/generated'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

// Every path in the OpenAPI schema that has a GET operation, so a typo or a removed endpoint
// fails type-checking instead of returning a 404 at runtime.
export type GetPath = {
  [P in keyof paths]: paths[P] extends { get: object } ? P : never
}[keyof paths]

type GetOperation<P extends GetPath> = paths[P] extends { get: infer Op } ? Op : never
type Parameters<P extends GetPath> =
  GetOperation<P> extends { parameters: infer Params } ? Params : never

type QueryParams<P extends GetPath> =
  Parameters<P> extends { query?: infer Query } ? Exclude<Query, undefined> : never
type PathParams<P extends GetPath> =
  Parameters<P> extends { path: infer Path } ? Exclude<Path, undefined> : never

export type GetResponse<P extends GetPath> =
  GetOperation<P> extends {
    responses: { 200: { content: { 'application/json': infer Body } } }
  }
    ? Body
    : never

type IfDefined<T, Shape> = [T] extends [never] ? object : Shape

export type GetOptions<P extends GetPath> = IfDefined<QueryParams<P>, { query?: QueryParams<P> }> &
  IfDefined<PathParams<P>, { params: PathParams<P> }> & {
    /** Names the resource in error messages: "Failed to fetch <resource>". */
    resource: string
    /** Non-2xx statuses whose JSON body is still a valid response, such as readiness's 503. */
    acceptStatuses?: number[]
  }

export function buildApiUrl(path: string, searchParams?: URLSearchParams) {
  const url = new URL(path, API_BASE_URL || window.location.origin)
  if (searchParams) {
    url.search = searchParams.toString()
  }

  if (!API_BASE_URL) {
    return `${url.pathname}${url.search}`
  }

  return url.toString()
}

function fillPathParams(path: string, params: Record<string, string | number> | undefined) {
  if (!params) {
    return path
  }
  // Encode each value so ids with '/', '?' or '#' can't escape their path segment.
  return path.replace(/\{(\w+)\}/g, (_, name: string) => encodeURIComponent(String(params[name])))
}

function toSearchParams(query: Record<string, unknown> | undefined) {
  if (!query) {
    return undefined
  }
  const searchParams = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value))
    }
  }
  return searchParams
}

export async function apiGet<P extends GetPath>(
  path: P,
  options: GetOptions<P>,
): Promise<GetResponse<P>> {
  const { resource, acceptStatuses = [] } = options
  const { query, params } = options as {
    query?: Record<string, unknown>
    params?: Record<string, string | number>
  }
  const url = buildApiUrl(fillPathParams(path, params), toSearchParams(query))

  let response: Response
  try {
    response = await fetch(url, { headers: { Accept: 'application/json' } })
  } catch (error) {
    // fetch() rejects with a TypeError only when the request never got a response.
    if (error instanceof TypeError) {
      throw new Error(`Failed to fetch ${resource}. Is the backend server running on port 8000?`)
    }
    throw error
  }

  if (!response.ok && !acceptStatuses.includes(response.status)) {
    throw new ApiError(`Failed to fetch ${resource} (HTTP ${response.status}).`, response.status)
  }

  return (await response.json()) as GetResponse<P>
}
