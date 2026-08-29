import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { operationsService } from '../services/operationsService'
import type { LiveTrip } from '../types'
import { LiveTripsPage } from './LiveTripsPage'

vi.mock('../services/operationsService', () => ({
  operationsService: {
    listLiveTrips: vi.fn(),
    getRouteDashboardSummary: vi.fn(),
    getLiveTripEvents: vi.fn(),
    getLiveTripLocations: vi.fn(),
  },
}))

vi.mock('../components/OpenStreetMapPanel', () => ({
  OpenStreetMapPanel: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="live-map">{children}</div>
  ),
}))

const liveTrip = {
  routeId: 'route-1',
  routeCode: 'ROUTE-20260829-A059EF',
  routeName: 'PCID202608292H001 - Load 1',
  driverName: 'QA Driver',
  vehicleCode: 'WP QA-1401',
  tripStatus: 'active',
  routeStatus: 'in_progress',
  latestLocation: { latitude: 6.91, longitude: 79.87, recordedAt: 'Now' },
  progress: { totalStops: 6, completedStops: 0 },
  latestEvent: null,
  navigation: {
    currentStopId: 'stop-1',
    currentParcelCode: 'QA-ORD-12-02',
    currentCustomerName: 'QA Customer 12-2',
    status: 'navigating',
    startedAt: '2026-08-29T04:15:00Z',
  },
} as unknown as LiveTrip

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(operationsService.listLiveTrips).mockResolvedValue([liveTrip])
  vi.mocked(operationsService.getRouteDashboardSummary).mockResolvedValue({})
  vi.mocked(operationsService.getLiveTripEvents).mockResolvedValue([])
  vi.mocked(operationsService.getLiveTripLocations).mockResolvedValue([])
})

afterEach(cleanup)

describe('LiveTripsPage', () => {
  it('shows the active vehicle and current FleetOpt navigation parcel', async () => {
    render(<LiveTripsPage />)

    expect(await screen.findByText('WP QA-1401')).toBeInTheDocument()
    expect(screen.getByText('QA-ORD-12-02')).toBeInTheDocument()
    expect(screen.getByText('QA Customer 12-2')).toBeInTheDocument()
    expect(screen.getByText('Navigating')).toBeInTheDocument()
    expect(screen.getByText('0/6')).toBeInTheDocument()
  })
})
