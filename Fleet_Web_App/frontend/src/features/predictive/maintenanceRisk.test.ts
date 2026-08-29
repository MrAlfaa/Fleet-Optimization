import { describe, expect, it } from 'vitest'
import type { MaintenancePrediction } from '../../types'
import { summarizeLatestFleetRisk } from './maintenanceRisk'

const prediction = (overrides: Partial<MaintenancePrediction>): MaintenancePrediction => ({
  id: 'prediction', vehicleId: 'vehicle', vehicleRegistration: 'WP CAA-1000', vehicleCode: 'FLEET-1',
  risk: 'low', probability30Days: 0.02, probability2000Km: 0.01, systemRisks: [],
  planningStatus: 'no_near_term_failure_indicated', planningWindow: null, dataQuality: 'good', defaultedFields: [],
  reviewStatus: 'not_required', dispatchHold: false, modelVersion: 'v1', featureSchemaVersion: '3.0',
  createdAt: '2026-08-24T08:00:00Z', featureHash: 'hash', reviewId: '', ...overrides,
})

describe('summarizeLatestFleetRisk', () => {
  it('counts one latest prediction per vehicle instead of historical rows', () => {
    const summary = summarizeLatestFleetRisk([
      prediction({ id: 'old-a', vehicleId: 'a', risk: 'critical', dispatchHold: true, createdAt: '2026-08-20T08:00:00Z' }),
      prediction({ id: 'new-a', vehicleId: 'a', risk: 'low', dispatchHold: false, createdAt: '2026-08-24T08:00:00Z' }),
      prediction({ id: 'new-b', vehicleId: 'b', risk: 'critical', dispatchHold: true, dataQuality: 'limited', createdAt: '2026-08-24T07:00:00Z' }),
    ])

    expect(summary.evaluated).toBe(2)
    expect(summary.critical).toBe(1)
    expect(summary.held).toBe(1)
    expect(summary.goodQuality).toBe(1)
    expect(summary.latestByVehicle.get('a')?.id).toBe('new-a')
  })
})
