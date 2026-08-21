import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './apiClient'

describe('apiClient.download', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('returns a blob and filename from content disposition', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('report', {
      status: 200,
      headers: { 'Content-Type': 'text/csv', 'Content-Disposition': 'attachment; filename=demand.csv' },
    })))

    const result = await apiClient.download('/demand/export')
    expect(result.filename).toBe('demand.csv')
    expect(await result.blob.text()).toBe('report')
  })
})

describe('apiClient.upload', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('sends FormData without forcing a JSON content type', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ success: true, message: 'ok', data: {} }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }))
    vi.stubGlobal('fetch', fetchMock)
    const formData = new FormData()
    formData.append('image', new File(['image'], 'vehicle.webp', { type: 'image/webp' }))

    await apiClient.upload('/vehicles/vehicle-1/image', formData)

    const headers = new Headers(fetchMock.mock.calls[0][1]?.headers)
    expect(headers.has('Content-Type')).toBe(false)
    expect(fetchMock.mock.calls[0][1]?.body).toBe(formData)
  })
})
