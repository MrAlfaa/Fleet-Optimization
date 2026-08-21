import { describe, expect, it } from 'vitest'
import { nearestSriLankaZone } from './operationalZones'

describe('nearestSriLankaZone', () => {
  it('maps Colombo coordinates to Colombo Central', () => {
    const zone = nearestSriLankaZone({ latitude: 6.9271, longitude: 79.8612 })
    expect(zone.id).toBe('LK_colombo_central')
    expect(zone.distanceKm).toBeLessThan(0.1)
  })
})
