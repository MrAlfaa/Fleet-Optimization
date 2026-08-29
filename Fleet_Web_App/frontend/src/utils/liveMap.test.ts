import { describe, expect, it } from 'vitest'
import type { LiveTrip, LiveTripLocation } from '../types'
import { buildLiveMapView } from './liveMap'

const trip = (overrides: Partial<LiveTrip> = {}): LiveTrip => ({
  routeId: 'route-1',
  routeCode: 'ROUTE-001',
  routeName: 'Colombo route',
  driverName: 'Driver One',
  vehicleCode: 'EV-001',
  tripStatus: 'active',
  routeStatus: 'in_progress',
  latestLocation: {
    latitude: 6.9271,
    longitude: 79.8612,
    recordedAt: '2026-08-15T10:00:00Z',
  },
  progress: { totalStops: 4, completedStops: 2 },
  latestEvent: null,
  navigation: {
    currentStopId: '', currentParcelCode: '', currentCustomerName: '', status: 'idle', startedAt: '',
  },
  ...overrides,
})

describe('buildLiveMapView', () => {
  it('creates real trip markers, a chronological trail, and aggregate progress', () => {
    const locations: LiveTripLocation[] = [
      { id: 'new', latitude: 6.93, longitude: 79.87, recordedAt: '2026-08-15T10:01:00Z' },
      { id: 'old', latitude: 6.92, longitude: 79.86, recordedAt: '2026-08-15T09:59:00Z' },
    ]

    const view = buildLiveMapView([
      trip(),
      trip({ routeId: 'route-2', routeCode: 'ROUTE-002', vehicleCode: 'EV-002', progress: { totalStops: 3, completedStops: 1 } }),
    ], locations)

    expect(view.markers).toHaveLength(2)
    expect(view.markers[0]).toMatchObject({
      id: 'route-1',
      label: '1',
      title: 'ROUTE-001 - Driver One',
      subtitle: 'EV-001 | 2/4 stops | 2026-08-15T10:00:00Z',
    })
    expect(view.trail).toEqual([
      { latitude: 6.92, longitude: 79.86 },
      { latitude: 6.93, longitude: 79.87 },
    ])
    expect(view.progress).toEqual({ completedStops: 3, totalStops: 7 })
    expect(view.selectedTrip?.routeId).toBe('route-1')
  })

  it('excludes trips and trail entries with invalid or missing coordinates', () => {
    const view = buildLiveMapView([
      trip({ routeId: 'missing', latestLocation: null }),
      trip({ routeId: 'invalid', latestLocation: { latitude: 120, longitude: 79.86, recordedAt: 'now' } }),
    ], [
      { id: 'bad', latitude: Number.NaN, longitude: 79.86, recordedAt: 'now' },
    ])

    expect(view.markers).toEqual([])
    expect(view.trail).toEqual([])
    expect(view.selectedTrip?.routeId).toBe('missing')
  })
})
