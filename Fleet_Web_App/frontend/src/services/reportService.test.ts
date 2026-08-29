import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './apiClient'
import { reportService } from './reportService'

vi.mock('./apiClient', () => ({ apiClient: { download: vi.fn() } }))

describe('reportService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(apiClient.download).mockResolvedValue({ blob: new Blob(), filename: 'report.xlsx' })
  })

  it('serializes a specialized report query without changing its filters', async () => {
    await reportService.export({
      format: 'xlsx',
      report_type: 'vehicle_maintenance',
      vehicle_id: 'vehicle-1',
      vehicle_category: 'bus',
      assessment_result: 'high',
      workflow_status: 'inspection',
      inspection_status: 'assigned',
      start_date: '2026-08-01',
      end_date: '2026-08-27',
    })

    expect(apiClient.download).toHaveBeenCalledWith('/reports/export', {
      query: {
        format: 'xlsx',
        report_type: 'vehicle_maintenance',
        vehicle_id: 'vehicle-1',
        vehicle_category: 'bus',
        assessment_result: 'high',
        workflow_status: 'inspection',
        inspection_status: 'assigned',
        start_date: '2026-08-01',
        end_date: '2026-08-27',
      },
    })
  })

  it('retains the generic positional export call', async () => {
    await reportService.export('pdf', '2026-08-01', '2026-08-27')
    expect(apiClient.download).toHaveBeenCalledWith('/reports/export', {
      query: { format: 'pdf', start_date: '2026-08-01', end_date: '2026-08-27' },
    })
  })

  it('keeps consolidation and driver filters in specialized export queries', async () => {
    await reportService.export({
      format: 'xlsx',
      report_type: 'consolidation_details',
      consolidation_id: 'PCID202608291H001',
      consolidation_status: 'approved',
      delivery_period: 'first_half',
    })
    expect(apiClient.download).toHaveBeenCalledWith('/reports/export', {
      query: {
        format: 'xlsx',
        report_type: 'consolidation_details',
        consolidation_id: 'PCID202608291H001',
        consolidation_status: 'approved',
        delivery_period: 'first_half',
      },
    })
  })
})
