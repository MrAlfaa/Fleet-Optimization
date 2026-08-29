import { describe, expect, it } from 'vitest'
import { deriveReadinessCapacity } from './readinessCapacity'

describe('deriveReadinessCapacity', () => {
  it('derives ready, warning, gap, and blocked counts without double-counting warnings', () => {
    const capacity = deriveReadinessCapacity({
      requiredVehicles: 12,
      eligibleVehicles: 9,
      warningVehicles: 2,
      blockedVehicles: 3,
    })

    expect(capacity).toMatchObject({
      required: 12,
      eligible: 9,
      ready: 7,
      warning: 2,
      gap: 3,
      blocked: 3,
      spare: 0,
      utilizationPercent: 75,
    })
    expect(capacity.ready + capacity.warning).toBe(capacity.eligible)
  })

  it('sanitizes inconsistent service data and reports spare eligible capacity', () => {
    const capacity = deriveReadinessCapacity({
      requiredVehicles: 4.8,
      eligibleVehicles: 8.4,
      warningVehicles: 99,
      blockedVehicles: -3,
    })

    expect(capacity).toMatchObject({
      required: 5,
      eligible: 8,
      ready: 0,
      warning: 8,
      gap: 0,
      blocked: 0,
      spare: 3,
      utilizationPercent: 100,
    })
  })
})
