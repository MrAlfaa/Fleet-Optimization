import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { ParcelConsolidationPage } from './ParcelConsolidationPage'

const { consolidation, createConsolidation } = vi.hoisted(() => ({ consolidation: vi.fn(), createConsolidation: vi.fn() }))

consolidation.mockResolvedValue({
  batch_key: 'colombo_central_branch:2026-08-30:first_half',
  delivery_date: '2026-08-30',
  delivery_period: 'first_half',
  parcel_count: 2,
  eligible_count: 2,
  exception_count: 0,
  excluded_count: 0,
  cluster_method: 'hdbscan',
  parcel_points: [
    { parcel_id: 'parcel-1', order_code: 'ORD-1', latitude: 6.9271, longitude: 79.8612, region_id: 0 },
    { parcel_id: 'parcel-2', order_code: 'ORD-2', latitude: 6.9371, longitude: 79.8712, region_id: 0 },
  ],
  regions: [{
    region_id: 0,
    parcel_count: 2,
    centroid: { latitude: 6.9271, longitude: 79.8612 },
    parcel_ids: ['parcel-1', 'parcel-2'],
  }],
  exceptions: [],
  excluded_orders: [],
  demand_context: { available: false, required_vehicle_shifts: null, high_demand_zones: [] },
})
createConsolidation.mockResolvedValue({
  reused: false,
  consolidation: {
    consolidation_id: 'PCID202608301H001',
    status: 'active',
    delivery_date: '2026-08-30',
    delivery_period: 'first_half',
    parcel_count: 2,
    parcel_ids: ['parcel-1', 'parcel-2'],
    parcel_points: [],
    regions: [],
  },
  exceptions: [],
})

vi.mock('../services/loadOptimizationService', () => ({
  loadOptimizationService: { consolidation, createConsolidation },
}))
vi.mock('../components/OpenStreetMapPanel', () => ({ OpenStreetMapPanel: () => <div>Cluster map</div> }))

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{JSON.stringify({ path: location.pathname, search: location.search, state: location.state })}</output>
}

describe('ParcelConsolidationPage', () => {
  it('uses Parcel Gallery records instead of exposing CSV upload', async () => {
    render(<MemoryRouter initialEntries={['/parcel-consolidation']}><Routes>
      <Route element={<><ParcelConsolidationPage /><LocationProbe /></>} path="/parcel-consolidation" />
      <Route element={<LocationProbe />} path="/route-planning" />
    </Routes></MemoryRouter>)

    expect(await screen.findByText(/Live Parcel Gallery source/i)).toBeInTheDocument()
    expect(screen.queryByText(/CSV/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/file/i)).not.toBeInTheDocument()
    expect(screen.getByText('2 parcels')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Optimize all regions/i }))
    await waitFor(() => expect(createConsolidation).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/route-planning'))
    expect(screen.getByTestId('location')).toHaveTextContent('PCID202608301H001')
  })
})
