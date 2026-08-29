import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { intelligenceService } from '../services/intelligenceService'
import type { FleetReadiness } from '../types'
import { FleetReadinessPage } from './FleetReadinessPage'


vi.mock('../services/intelligenceService', () => ({ intelligenceService: { getFleetReadiness: vi.fn() } }))
vi.mock('../features/readiness/FleetCapacityVisualization', () => ({
  FleetCapacityVisualization: ({ readiness }: { readiness: { requiredVehicles: number; eligibleVehicles: number } }) => (
    <div data-testid="capacity-deck">{readiness.eligibleVehicles}/{readiness.requiredVehicles} covered</div>
  ),
}))

const response: FleetReadiness = {
  forecastDate: '2027-01-01', requiredVehicles: 8, eligibleVehicles: 6, warningVehicles: 2,
  blockedVehicles: 3, maintenanceVehicles: 1, capacityGap: 2,
  activeForecastRun: {
    model_run_id: 'run-approved-30', model_version: 'demand-v2.1',
    forecast_start_date: '2027-01-01T00:00:00+00:00', forecast_end_date: '2027-01-30T00:00:00+00:00',
    horizon_days: 30, records_generated: 450, zones_count: 15, source_requested: 'model',
    effective_source: 'model', fallback_used: false,
    run_type: 'controlled', generated_at: '2026-08-28T08:30:00Z', activated_at: '2026-08-28T08:30:00Z',
    request_fingerprint: 'forecast-30-model',
    planning_window: {
      basis: 'artifact_dataset_end', dataset_end_date: '2026-12-31',
      forecast_start_date: '2027-01-01T00:00:00+00:00', forecast_end_date: '2027-01-30T00:00:00+00:00',
      horizon_days: 30,
    },
  },
  highDemandZones: [{ operationalZoneId: 'LK_borella', zoneDisplayName: 'Borella', predictedDemand: 21, actualDemand: null, demandLevel: 'high', estimatedRequiredVehicles: 2, recommendedAction: 'Reserve additional capacity.' }],
  vehicleReadiness: [], operationalConflicts: [],
  recommendations: [{ type: 'capacity_shortage', severity: 'high', message: 'Reserve two additional vehicles.' }],
  dataContext: 'colombo_operational_forecast', dataContextNote: 'Colombo operational demand forecast.',
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(intelligenceService.getFleetReadiness).mockResolvedValue(response)
})

afterEach(cleanup)

describe('FleetReadinessPage', () => {
  it('connects forecast capacity to the accessible dispatch capacity deck', async () => {
    render(<FleetReadinessPage />)

    expect(await screen.findByRole('heading', { name: 'Fleet Readiness' })).toBeInTheDocument()
    expect(screen.getByTestId('capacity-deck')).toHaveTextContent('6/8 covered')
    expect(screen.getByText('Borella')).toBeInTheDocument()
    expect(screen.getByText('Reserve two additional vehicles.')).toBeInTheDocument()
    expect(screen.getByLabelText('Forecast date')).toHaveValue('2027-01-01')
    expect(screen.getByLabelText('Forecast date')).toHaveAttribute('min', '2027-01-01')
    expect(screen.getByLabelText('Forecast date')).toHaveAttribute('max', '2027-01-30')
  })

  it('recalculates readiness for the selected forecast date', async () => {
    render(<FleetReadinessPage />)
    await screen.findByRole('heading', { name: 'Fleet Readiness' })

    fireEvent.change(screen.getByLabelText('Forecast date'), { target: { value: '2027-01-02' } })

    await waitFor(() => expect(intelligenceService.getFleetReadiness).toHaveBeenLastCalledWith('2027-01-02'))
  })
})
