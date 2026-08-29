import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './apiClient'
import { fleetService } from './fleetService'

vi.mock('./apiClient', () => ({ apiClient: { post: vi.fn(), get: vi.fn(), put: vi.fn(), patch: vi.fn(), delete: vi.fn(), upload: vi.fn() } }))

describe('fleetService maintenance lifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.get).mockImplementation(async (path) => path === '/vehicles' ? { items: [], page: 1, limit: 100, total: 0, pages: 0 } : { id: 'work-1', vehicle_id: 'vehicle-1', work_order_status: 'in_progress' })
    vi.mocked(apiClient.patch).mockResolvedValue({ id: 'work-1', vehicle_id: 'vehicle-1' })
  })

  it('uses exact lifecycle endpoints and completion payload', async () => {
    await fleetService.approveMaintenance('work-1')
    await fleetService.startMaintenance('work-1')
    await fleetService.completeMaintenance('work-1', { actual_cost: 24500, completion_evidence: 'Brake pads replaced and road test passed.', technician_name: 'A. Silva', service_center: 'Colombo Workshop' })
    expect(apiClient.patch).toHaveBeenNthCalledWith(1, '/maintenance/work-1/approve', {})
    expect(apiClient.patch).toHaveBeenNthCalledWith(2, '/maintenance/work-1/start', {})
    expect(apiClient.patch).toHaveBeenNthCalledWith(3, '/maintenance/work-1/complete', { actual_cost: 24500, completion_evidence: 'Brake pads replaced and road test passed.', technician_name: 'A. Silva', service_center: 'Colombo Workshop' })
  })

  it('requires the caller to provide a cancellation reason', async () => {
    await fleetService.cancelMaintenance('work-9', 'Duplicate work order')
    expect(apiClient.patch).toHaveBeenCalledWith('/maintenance/work-9/cancel', { reason: 'Duplicate work order' })
  })
})
