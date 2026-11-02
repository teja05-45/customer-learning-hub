/**
 * Thin fetch client.
 *
 * The backend always answers failures with
 * `{ error: { code, message, details } }`, so every screen gets a message it
 * can display rather than a bare status code.
 */

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '') + '/api/v1'
const DEMO_USER_KEY = 'clh.demoUserId'

export class ApiError extends Error {
  status: number
  code: string
  details: unknown

  constructor(message: string, status: number, code: string, details: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

export function getDemoUserId(): string | null {
  return window.localStorage.getItem(DEMO_USER_KEY)
}

export function setDemoUserId(id: string | null) {
  if (id) window.localStorage.setItem(DEMO_USER_KEY, id)
  else window.localStorage.removeItem(DEMO_USER_KEY)
}

type QueryValue = string | number | boolean | null | undefined | Array<string | number>

export function toQuery(params: Record<string, QueryValue>): string {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === null || value === undefined || value === '') return
    if (Array.isArray(value)) {
      value.forEach((entry) => search.append(key, String(entry)))
    } else {
      search.append(key, String(value))
    }
  })
  const query = search.toString()
  return query ? `?${query}` : ''
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  const demoUserId = getDemoUserId()
  if (demoUserId) headers.set('X-Demo-User-Id', demoUserId)

  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  } catch {
    throw new ApiError(
      'The API could not be reached. Check that the backend is running, then retry.',
      0,
      'network_error',
      null,
    )
  }

  if (response.status === 204) return undefined as T

  const isJson = (response.headers.get('content-type') ?? '').includes('application/json')
  const payload = isJson ? await response.json().catch(() => null) : null

  if (!response.ok) {
    const envelope = payload as { error?: { code?: string; message?: string; details?: unknown } } | null
    throw new ApiError(
      envelope?.error?.message ?? `Request failed with status ${response.status}.`,
      response.status,
      envelope?.error?.code ?? 'http_error',
      envelope?.error?.details ?? null,
    )
  }

  return payload as T
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: 'PATCH', body: body === undefined ? undefined : JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  downloadCsv: async (path: string, filename: string) => {
    const headers = new Headers()
    const demoUserId = getDemoUserId()
    if (demoUserId) headers.set('X-Demo-User-Id', demoUserId)
    const response = await fetch(`${API_BASE}${path}`, { headers })
    if (!response.ok) {
      throw new ApiError('The export could not be generated.', response.status, 'export_failed', null)
    }
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return 'Something went wrong.'
}

export function fieldErrors(error: unknown): Record<string, string> {
  if (!(error instanceof ApiError) || !Array.isArray(error.details)) return {}
  const result: Record<string, string> = {}
  for (const detail of error.details as { field?: string; message?: string }[]) {
    if (detail.field) result[detail.field.split('.').pop() ?? detail.field] = detail.message ?? 'Invalid value'
  }
  return result
}
