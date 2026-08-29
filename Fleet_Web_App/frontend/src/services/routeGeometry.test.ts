import { describe, expect, it } from 'vitest'
import { mapRouteGeometryCoordinates } from './operationsService'

describe('mapRouteGeometryCoordinates', () => {
  it('maps backend latitude/longitude objects and drops invalid points', () => {
    expect(mapRouteGeometryCoordinates({
      geometry_source: 'osrm',
      coordinates: [
        { latitude: 6.9271, longitude: 79.8612 },
        { latitude: '6.9', longitude: '79.9' },
        { latitude: 999, longitude: 79.8 },
      ],
    })).toEqual([
      { latitude: 6.9271, longitude: 79.8612 },
      { latitude: 6.9, longitude: 79.9 },
    ])
  })
})
