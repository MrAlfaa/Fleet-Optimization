import { describe, expect, it } from 'vitest'
import type { DemandForecast, OperationalZoneOption } from '../../types'
import { aggregateForecastTrend, buildZoneSnapshots, forecastDates } from './forecastView'


const forecasts: DemandForecast[] = [
  {
    zoneId: 'LK_colombo_central', zone: 'Colombo Central', date: '2027-01-01', currentVolume: 12,
    actualAvailable: true, predictedVolume: 15, variance: 25, varianceOrders: 3, demandLevel: 'medium',
    requiredVehicles: 2, action: 'Monitor capacity', baselineForecast: 14, lowerBound: 9, upperBound: 20,
    modelVersion: 'fleetopt-demand-synthetic-v1', generatedAt: '2026-08-27T00:00:00Z',
  },
  {
    zoneId: 'LK_nugegoda', zone: 'Nugegoda', date: '2027-01-01', currentVolume: 10,
    actualAvailable: true, predictedVolume: 11, variance: 10, varianceOrders: 1, demandLevel: 'low',
    requiredVehicles: 1, action: 'Normal capacity', baselineForecast: 10, lowerBound: 6, upperBound: 15,
    modelVersion: 'fleetopt-demand-synthetic-v1', generatedAt: '2026-08-27T00:00:00Z',
  },
  {
    zoneId: 'LK_colombo_central', zone: 'Colombo Central', date: '2027-01-02', currentVolume: 0,
    actualAvailable: false, predictedVolume: 27, variance: 0, varianceOrders: null, demandLevel: 'very_high',
    requiredVehicles: 3, action: 'Allocate capacity', baselineForecast: 26, lowerBound: 20, upperBound: 34,
    modelVersion: 'fleetopt-demand-synthetic-v1', generatedAt: '2026-08-27T00:00:00Z',
  },
]

const zones: OperationalZoneOption[] = [
  { id: 'LK_colombo_central', name: 'Colombo Central', latitude: 6.9271, longitude: 79.8612, serviceRadiusKm: 12 },
  { id: 'LK_nugegoda', name: 'Nugegoda', latitude: 6.8649, longitude: 79.8997, serviceRadiusKm: 12 },
]

describe('forecast view helpers', () => {
  it('aggregates all zone records by forecast date', () => {
    expect(aggregateForecastTrend(forecasts)).toEqual([
      { date: '2027-01-01', label: 'Jan 1', actual: 22, actualAvailable: true, predicted: 26 },
      { date: '2027-01-02', label: 'Jan 2', actual: null, actualAvailable: false, predicted: 27 },
    ])
  })

  it('uses backend demand level and required vehicles for zone snapshots', () => {
    const snapshots = buildZoneSnapshots(zones, forecasts, '2027-01-02')

    expect(snapshots[0]).toMatchObject({ id: 'LK_colombo_central', demandLevel: 'very_high', requiredVehicles: 3, predicted: 27 })
    expect(snapshots[1]).toMatchObject({ id: 'LK_nugegoda', demandLevel: 'low', requiredVehicles: 0, predicted: 0 })
  })

  it('returns sorted unique dates', () => {
    expect(forecastDates(forecasts)).toEqual(['2027-01-01', '2027-01-02'])
  })
})
