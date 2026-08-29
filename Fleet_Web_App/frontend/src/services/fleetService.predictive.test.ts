import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './apiClient'
import { fleetService } from './fleetService'

vi.mock('./apiClient', () => ({
  apiClient: { post: vi.fn(), get: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn(), upload: vi.fn(), download: vi.fn() },
}))

describe('fleetService predictive maintenance', () => {
  beforeEach(() => vi.clearAllMocks())

  it('sends an explicit review request without accepting raw model features', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ id: 'prediction-1', vehicle_id: 'vehicle-1', risk_level: 'high' })
    await fleetService.recalculateMaintenanceRisk('vehicle-1', { requestReview: true })

    expect(apiClient.post).toHaveBeenCalledWith('/predictive-maintenance/vehicles/vehicle-1/recalculate', {
      trigger: 'manual_recalculation', request_review: true,
    })
  })

  it('downloads the vehicle template and uploads the selected workbook', async () => {
    vi.mocked(apiClient.download).mockResolvedValue({ blob: new Blob(), filename: 'history.xlsx' })
    await fleetService.downloadMaintenanceHistoryTemplate('vehicle-1')
    expect(apiClient.download).toHaveBeenCalledWith('/maintenance/history/template', { query: { vehicle_id: 'vehicle-1' } })

    const file = new File(['xlsx'], 'history.xlsx')
    vi.mocked(apiClient.upload).mockResolvedValue({ imported_count: 2 })
    await fleetService.importMaintenanceHistory('vehicle-1', file)
    const body = vi.mocked(apiClient.upload).mock.calls[0][1] as FormData
    expect(body.get('vehicle_id')).toBe('vehicle-1')
    expect(body.get('workbook')).toBe(file)
  })
})
