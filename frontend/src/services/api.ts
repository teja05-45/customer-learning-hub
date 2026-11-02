/**
 * Thin fetch client.
 *
 * The backend always answers failures with
 * `{ error: { code, message, details } }`, so every screen gets a message it
 * can display rather than a bare status code.
 */

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '') + '/api/v1'

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
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers, credentials: 'include' })
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
  /**
   * Download a CSV and return the filename the server actually used.
   *
   * The response is checked *before* any success message is shown: a failed
   * request surfaces the API's own error envelope, not a generic message, and an
   * empty body is treated as a failure rather than a silent no-op download.
   */
  downloadCsv: async (path: string, fallbackFilename: string): Promise<string> => {
    let response: Response
    try {
      response = await fetch(`${API_BASE}${path}`, { credentials: 'include' })
    } catch {
      throw new ApiError(
        'The API could not be reached, so nothing was downloaded.',
        0,
        'network_error',
        null,
      )
    }
    if (!response.ok) {
      const isJson = (response.headers.get('content-type') ?? '').includes('application/json')
      const payload = isJson ? await response.json().catch(() => null) : null
      const envelope = payload as {
        error?: { message?: string; code?: string; details?: unknown }
      } | null
      throw new ApiError(
        envelope?.error?.message ?? `The export failed with status ${response.status}.`,
        response.status,
        envelope?.error?.code ?? 'export_failed',
        envelope?.error?.details ?? null,
      )
    }
    const blob = await response.blob()
    if (blob.size === 0) {
      throw new ApiError('The server returned an empty file.', response.status, 'export_empty', null)
    }
    const disposition = response.headers.get('content-disposition') ?? ''
    const match = /filename="?([^";]+)"?/.exec(disposition)
    const filename = match?.[1] ?? fallbackFilename
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    return filename
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
