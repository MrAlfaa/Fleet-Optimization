import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './apiClient'
import { forecastService } from './forecastService'

vi.mock('./apiClient', () => ({ apiClient: { get: vi.fn(), post: vi.fn(), download: vi.fn() } }))

describe('forecastService controlled runs', () => {
  beforeEach(() => vi.clearAllMocks())

  it('generates only a model-backed persisted forecast for an allowed horizon', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ reused_active_run: false, active_run: {} })

    await forecastService.generateForecast(14)

    expect(apiClient.post).toHaveBeenCalledWith('/demand/refresh', {
      days: 14,
      source: 'model',
      save_to_database: true,
    })
  })

  it('requests the ten most recent cycles and returns their items', async () => {
    const items = [{ model_run_id: 'run-1' }]
    vi.mocked(apiClient.get).mockResolvedValue({ items })

    await expect(forecastService.listForecastRuns(10)).resolves.toEqual(items)
    expect(apiClient.get).toHaveBeenCalledWith('/demand/runs', { query: { limit: 10 } })
  })

  it('loads saved rows for one validated forecast run', async () => {
    const detail = { run: { model_run_id: 'run-1' }, items: [], total: 0 }
    vi.mocked(apiClient.get).mockResolvedValue(detail)

    await expect(forecastService.getForecastRun('run-1')).resolves.toEqual(detail)
    expect(apiClient.get).toHaveBeenCalledWith('/demand/runs/run-1', { query: { page: 1, limit: 500 } })
  })
})
