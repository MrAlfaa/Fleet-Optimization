import { clearStoredSession, getAccessToken } from './sessionStore'

interface BackendResponse<T> {
  success: boolean
  message: string
  data: T
}

interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  query?: Record<string, string | number | boolean | null | undefined>
  skipAuth?: boolean
}

export class ApiError extends Error {
  status: number
  data: unknown

  constructor(message: string, status: number, data?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'https://137-23-38-111.sslip.io/api'
).replace(/\/+$/, '')

function buildUrl(path: string, query?: RequestOptions['query']) {
  const cleanPath = path.startsWith('/') ? path : `/${path}`
  const url = new URL(`${API_BASE_URL}${cleanPath}`, window.location.origin)

  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value))
    }
  })

  return url.toString()
}

function validationErrorMessage(payload: unknown): string | undefined {
  if (typeof payload !== 'object' || payload === null) return undefined

  const response = payload as { data?: unknown; detail?: unknown }
  const errors = Array.isArray(response.data)
    ? response.data
    : Array.isArray(response.detail)
      ? response.detail
      : []
  const error = errors[0]
  if (typeof error !== 'object' || error === null) return undefined

  const issue = error as { loc?: unknown; msg?: unknown }
  if (typeof issue.msg !== 'string') return undefined

  const location = Array.isArray(issue.loc) ? issue.loc : []
  const fieldName = [...location]
    .reverse()
    .find((part) => typeof part === 'string' && part !== 'body')
  const fieldLabel = typeof fieldName === 'string'
    ? fieldName.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase())
    : 'Request'
  const message = issue.msg.replace(/^Value error,\s*/i, '')
  return `${fieldLabel}: ${message}`
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : await response.text()

  if (!response.ok) {
    const responseMessage = typeof payload === 'object' && payload !== null && 'message' in payload
        ? String((payload as { message?: string }).message)
        : typeof payload === 'object' && payload !== null && 'detail' in payload
          ? String((payload as { detail?: string }).detail)
          : `Request failed with status ${response.status}`
    const message = response.status === 422
      ? validationErrorMessage(payload) ?? responseMessage
      : responseMessage

    if (response.status === 401) {
      clearStoredSession()
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }

    throw new ApiError(message, response.status, payload)
  }

  if (typeof payload === 'object' && payload !== null && 'success' in payload) {
    const wrapped = payload as BackendResponse<T>
    if (!wrapped.success) {
      throw new ApiError(wrapped.message || 'Request failed', response.status, wrapped.data)
    }
    return wrapped.data
  }

  return payload as T
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, query, skipAuth, ...init } = options
  const token = getAccessToken()
  const requestHeaders = new Headers(headers)
  const isFormData = body instanceof FormData

  if (body !== undefined && !isFormData && !requestHeaders.has('Content-Type')) {
    requestHeaders.set('Content-Type', 'application/json')
  }
  if (token && !skipAuth) {
    requestHeaders.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(buildUrl(path, query), {
    ...init,
    headers: requestHeaders,
    body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
  })

  return parseResponse<T>(response)
}

async function download(path: string, options: RequestOptions = {}) {
  const { query, skipAuth, headers, body, ...init } = options
  void body
  const requestHeaders = new Headers(headers)
  const token = getAccessToken()
  if (token && !skipAuth) requestHeaders.set('Authorization', `Bearer ${token}`)
  const response = await fetch(buildUrl(path, query), { ...init, method: 'GET', headers: requestHeaders })
  if (!response.ok) {
    if (response.status === 401) {
      clearStoredSession()
      if (window.location.pathname !== '/login') window.location.assign('/login')
    }
    throw new ApiError(`Download failed with status ${response.status}`, response.status)
  }
  const disposition = response.headers.get('content-disposition') || ''
  const filename = disposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)/i)?.[1]?.replace(/"$/, '') || 'download'
  return { blob: await response.blob(), filename: decodeURIComponent(filename) }
}

export const apiClient = {
  get: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: 'GET' }),
  post: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>(path, { ...options, method: 'POST', body }),
  put: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>(path, { ...options, method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown, options?: RequestOptions) => request<T>(path, { ...options, method: 'PATCH', body }),
  delete: <T>(path: string, options?: RequestOptions) => request<T>(path, { ...options, method: 'DELETE' }),
  upload: <T>(path: string, formData: FormData, options?: RequestOptions) => request<T>(path, { ...options, method: 'POST', body: formData }),
  download,
}
