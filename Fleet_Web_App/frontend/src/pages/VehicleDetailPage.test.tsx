import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { VehicleDetailPage } from './VehicleDetailPage'
import { VehicleMaintenancePage } from './VehicleMaintenancePage'
import { AppShell } from '../components/Shell'
import { fleetService } from '../services/fleetService'
import type { MaintenancePrediction, MaintenanceRecord, Vehicle, VehiclePart } from '../types'

vi.mock('../services/fleetService', () => ({
  fleetService: {
    getVehicle: vi.fn(),
    listVehicleParts: vi.fn(),
    listMaintenanceRecords: vi.fn(),
    getCurrentMaintenancePrediction: vi.fn(),
    getMaintenancePredictionHistory: vi.fn(),
    recalculateMaintenanceRisk: vi.fn(),
    listInspections: vi.fn(),
    getAssessmentEligibility: vi.fn(),
    createCommissioningInspection: vi.fn(),
    downloadMaintenanceHistoryTemplate: vi.fn(),
    importMaintenanceHistory: vi.fn(),
  },
}))

vi.mock('../services/authService', () => ({
  authService: {
    getSession: () => ({
      id: 'admin-1', name: 'Admin User', email: 'admin@fleet.local', role: 'admin', organization: 'FleetOpt AI',
      permissions: [
        'vehicles.view', 'vehicles.update', 'maintenance.view', 'maintenance.manage', 'predictive.view', 'predictive.run',
        'vehicles.tab.overview', 'vehicles.tab.risk_assessment', 'vehicles.tab.maintenance',
        'vehicles.tab.parts_inspections', 'vehicles.tab.activity',
      ],
    }),
    logout: vi.fn(),
  },
}))

const vehicle: Vehicle = {
  id: 'vehicle-1', number: 'WP CAA-1208', registrationNumber: 'WP CAA-1208', vehicleCode: 'FLT-008',
  imageUrl: null, category: 'Van', vehicleCategory: 'van', fuelType: 'electric', inServiceDate: '2024-01-15',
  payloadCapacityKg: 1200, brand: 'BYD', modelName: 'T3', year: 2024, batteryCapacityKwh: 80,
  model: 'BYD T3', type: 'electric_van', assignedDriver: 'Unassigned', mileage: 68400, status: 'Active', risk: 'high',
  onboardingType: 'existing_fleet', commissioningStatus: 'passed',
}

const eligibility = {
  vehicleId: 'vehicle-1', onboardingType: 'existing_fleet' as const, eligible: true,
  status: 'new_assessment_available' as const, hasNewData: true, missingProfileFields: [], blockingReasons: [],
  requirements: {
    profile: { complete: true }, commissioningInspection: { complete: true },
    completedTrips: { current: 0, required: 5, complete: false },
    recordedDistanceKm: { current: 0, required: 100, complete: false },
    importedHistory: { current: 2, complete: true }, historyEvidence: { complete: true },
  },
}

const parts: VehiclePart[] = [{
  id: 'part-1', vehicleId: 'vehicle-1', name: 'Brake Pads', lastService: '2026-06-10', failures: 0,
  risk: 'low', riskScore: 12, status: 'healthy', predictedNext: 'Not scheduled', note: '', isActive: true,
}]

const records: MaintenanceRecord[] = [{
  id: 'record-1', vehicleId: 'vehicle-1', date: '2026-08-20', vehicle: 'WP CAA-1208', partName: 'Brake Pads',
  maintenanceType: 'Inspection', priority: 'high', service: 'Brake inspection', technician: 'A. Perera',
  cost: 'LKR 0', costValue: 0, status: 'Pending Parts',
}]

const assessment: MaintenancePrediction = {
  id: 'assessment-current', vehicleId: 'vehicle-1', vehicleRegistration: 'WP CAA-1208', vehicleCode: 'FLT-008',
  risk: 'high', probability30Days: 0.27, probability2000Km: 0.11,
  systemRisks: [{ key: 'braking', name: 'Braking', probability: 0.48, risk: 'high' }],
  planningStatus: 'planning_window_available', planningWindow: { minimumDays: 10, maximumDays: 35, minimumKm: 500, maximumKm: 1800 },
  dataQuality: 'good', defaultedFields: [], reviewStatus: 'cleared', dispatchHold: false,
  modelVersion: 'internal-v1', featureSchemaVersion: '2.0', createdAt: '2026-08-26T08:00:00Z', featureHash: 'hash-current', reviewId: 'review-1',
}

const pendingHistory: MaintenancePrediction = {
  ...assessment, id: 'assessment-pending', reviewStatus: 'pending', createdAt: '2026-08-25T08:00:00Z', featureHash: 'hash-pending',
}

beforeEach(() => {
  vi.mocked(fleetService.getVehicle).mockResolvedValue(vehicle)
  vi.mocked(fleetService.listVehicleParts).mockResolvedValue(parts)
  vi.mocked(fleetService.listMaintenanceRecords).mockResolvedValue(records)
  vi.mocked(fleetService.getCurrentMaintenancePrediction).mockResolvedValue(assessment)
  vi.mocked(fleetService.getMaintenancePredictionHistory).mockResolvedValue([assessment, pendingHistory])
  vi.mocked(fleetService.recalculateMaintenanceRisk).mockResolvedValue(assessment)
  vi.mocked(fleetService.listInspections).mockResolvedValue({ items: [], page: 1, limit: 100, total: 0, pages: 0 })
  vi.mocked(fleetService.getAssessmentEligibility).mockResolvedValue(eligibility)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

function renderWorkspace(entry = '/vehicles/vehicle-1') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <Routes><Route element={<VehicleDetailPage />} path="/vehicles/:vehicleId" /></Routes>
    </MemoryRouter>,
  )
}

describe('VehicleDetailPage unified workspace', () => {
  it('owns the five responsive workspace tabs and uses business terminology', async () => {
    renderWorkspace('/vehicles/vehicle-1?tab=risk-assessment')

    expect(await screen.findByRole('heading', { name: 'Vehicle Risk Assessment' })).toBeInTheDocument()
    for (const name of ['Overview', 'Risk Assessment', 'Maintenance', 'Parts & Inspections', 'Activity']) {
      expect(screen.getByRole('tab', { name })).toBeInTheDocument()
    }
    expect(screen.getByText('30-day service risk')).toBeInTheDocument()
    expect(screen.getByText('2,000-km service risk')).toBeInTheDocument()
    expect(screen.getByText('Maintenance planning range')).toBeInTheDocument()
    expect(screen.getByText('Inspection priority areas')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create New Assessment' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add to Inspection' })).toBeInTheDocument()
    expect(document.body).not.toHaveTextContent(/\b(?:ML|model|prediction)\b/i)
  })

  it('keeps maintenance and optional service inventory in their own tabs', async () => {
    renderWorkspace()
    await screen.findByText('WP CAA-1208')

    expect(screen.queryByText('Optional service inventory')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Maintenance' }))
    expect(await screen.findByRole('heading', { name: 'Service records' })).toBeInTheDocument()
    expect(screen.queryByText('Optional service inventory')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('tab', { name: 'Parts & Inspections' }))
    expect(await screen.findByRole('heading', { name: 'Optional service inventory' })).toBeInTheDocument()
    expect(screen.getByText(/parts are tracked only when the service team needs item-level history/i)).toBeInTheDocument()
  })

  it('shows only approved assessment history and explains the operational purpose', async () => {
    renderWorkspace('/vehicles/vehicle-1?tab=risk-assessment')

    expect(await screen.findByRole('heading', { name: 'Approved assessment history' })).toBeInTheDocument()
    expect(screen.getByText(/review near-term service risk/i)).toBeInTheDocument()
    expect(screen.getByText(/reassess after mileage, trip, inspection, or service records are updated/i)).toBeInTheDocument()
    expect(screen.queryByText(/same source data produces/i)).not.toBeInTheDocument()
    expect(screen.getByText('26 Aug 2026')).toBeInTheDocument()
    expect(screen.queryByText('25 Aug 2026')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Create New Assessment' }))
    await waitFor(() => expect(fleetService.recalculateMaintenanceRisk).toHaveBeenCalledWith('vehicle-1'))
  })

  it('blocks assessment while history is incomplete and offers controlled import', async () => {
    vi.mocked(fleetService.getCurrentMaintenancePrediction).mockResolvedValue(null)
    vi.mocked(fleetService.getMaintenancePredictionHistory).mockResolvedValue([])
    vi.mocked(fleetService.getAssessmentEligibility).mockResolvedValue({
      ...eligibility,
      eligible: false,
      status: 'building_history',
      hasNewData: false,
      blockingReasons: ['Import at least one completed historical service record'],
      requirements: {
        ...eligibility.requirements,
        importedHistory: { current: 0, complete: false },
        historyEvidence: { complete: false },
      },
    })

    renderWorkspace('/vehicles/vehicle-1?tab=risk-assessment')

    expect(await screen.findByText('Build service history')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create New Assessment' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Import Service History' })).toBeInTheDocument()
  })
})

describe('Task 4 routing and shell terminology', () => {
  it('redirects the old maintenance workspace to the unified maintenance tab', () => {
    function LocationProbe() {
      const location = useLocation()
      return <div data-testid="location">{location.pathname}{location.search}</div>
    }
    render(<MemoryRouter initialEntries={['/maintenance/vehicle/vehicle-1']}><Routes>
      <Route element={<VehicleMaintenancePage />} path="/maintenance/vehicle/:vehicleId" />
      <Route element={<LocationProbe />} path="/vehicles/:vehicleId" />
    </Routes></MemoryRouter>)

    expect(screen.getByTestId('location')).toHaveTextContent('/vehicles/vehicle-1?tab=maintenance')
  })

  it('uses business navigation labels for assessment work', () => {
    render(<MemoryRouter initialEntries={['/vehicles/vehicle-1']}><Routes>
      <Route element={<AppShell />} path="/vehicles/:vehicleId" />
    </Routes></MemoryRouter>)

    expect(screen.getByText('Risk Assessments')).toBeInTheDocument()
    expect(screen.getByText('Vehicle Workspace')).toBeInTheDocument()
    expect(screen.queryByText('Predictive Risk')).not.toBeInTheDocument()
  })
})
