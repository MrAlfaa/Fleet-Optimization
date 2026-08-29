import { describe, expect, it } from 'vitest'
import { nearestSriLankaZone } from './operationalZones'
import { SRI_LANKA_ZONES } from '../data/sriLankaZones'

describe('nearestSriLankaZone', () => {
  it('maps Colombo coordinates to Colombo Central', () => {
    const zone = nearestSriLankaZone({ latitude: 6.9271, longitude: 79.8612 })
    expect(zone.id).toBe('LK_colombo_central')
    expect(zone.distanceKm).toBeLessThan(0.1)
  })

  it('uses the complete fifteen-zone Colombo operating catalog', () => {
    expect(SRI_LANKA_ZONES).toHaveLength(15)
    expect(new Set(SRI_LANKA_ZONES.map((zone) => zone.id)).size).toBe(15)
    expect(SRI_LANKA_ZONES.map((zone) => zone.id)).toContain('LK_wattala')
    expect(SRI_LANKA_ZONES.map((zone) => zone.id)).toContain('LK_piliyandala')
  })
})
