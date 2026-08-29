import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetService } from '../services/fleetService'
import type { Vehicle, VehicleMaintenanceInspection } from '../types'
import { RepairDecisionPage } from './RepairDecisionPage'

vi.mock('../services/fleetService', () => ({ fleetService: { getInspection: vi.fn(), getVehicle: vi.fn(), decideInspection: vi.fn() } }))
vi.mock('../services/authService', () => ({ authService: { getSession: () => ({ id: 'manager-1', role: 'maintenance_manager', permissions: ['maintenance.manage'] }) } }))

const vehicle = { id: 'vehicle-1', registrationNumber: 'WP CAA-1208', vehicleCode: 'QA-EV-008', model: 'BYD T3' } as Vehicle
const inspection = {
  id: 'inspection-1', vehicleId: 'vehicle-1', status: 'decision_pending', priority: 'high', inspectionAreas: ['Braking'],
  checklist: [{ key: 'braking', label: 'Braking', outcome: 'failed', remark: 'Brake fade detected' }], summary: 'Brake system requires a service decision',
  startedAt: '2026-08-27T08:00:00Z', completedAt: '2026-08-27T09:00:00Z', workOrderId: null,
} as VehicleMaintenanceInspection

function renderPage() {
  return render(<MemoryRouter initialEntries={['/maintenance/inspections/inspection-1/decision']}><Routes><Route path="/maintenance/inspections/:inspectionId/decision" element={<RepairDecisionPage />} /><Route path="/maintenance" element={<div>Command center</div>} /><Route path="/vehicles/:vehicleId" element={<div>Vehicle maintenance</div>} /></Routes></MemoryRouter>)
}

beforeEach(() => {
  vi.mocked(fleetService.getInspection).mockResolvedValue(inspection)
  vi.mocked(fleetService.getVehicle).mockResolvedValue(vehicle)
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

describe('RepairDecisionPage', () => {
  it('submits a return-to-service decision with required notes', async () => {
    vi.mocked(fleetService.decideInspection).mockResolvedValue({ ...inspection, status: 'returned_to_service' })
    renderPage()
    await screen.findByText('Brake fade detected')
    fireEvent.click(screen.getByRole('button', { name: 'Return to Service' }))
    fireEvent.change(screen.getByLabelText('Decision notes'), { target: { value: 'Road test completed and braking response is within limits.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Return to Service' }))
    await waitFor(() => expect(fleetService.decideInspection).toHaveBeenCalledWith('inspection-1', {
      decision: 'returned_to_service', notes: 'Road test completed and braking response is within limits.',
    }))
  })

  it('submits a complete maintenance-required decision payload', async () => {
    vi.mocked(fleetService.decideInspection).mockResolvedValue({ ...inspection, status: 'maintenance_required', workOrderId: 'work-1' })
    renderPage()
    await screen.findByText('Brake fade detected')
    fireEvent.click(screen.getByRole('button', { name: 'Maintenance Required' }))
    fireEvent.change(screen.getByLabelText('Decision notes'), { target: { value: 'Brake system needs corrective work before dispatch.' } })
    fireEvent.change(screen.getByLabelText('Maintenance system'), { target: { value: 'braking' } })
    fireEvent.change(screen.getByLabelText('Issue type'), { target: { value: 'Brake fade under load' } })
    fireEvent.change(screen.getByLabelText('Priority'), { target: { value: 'high' } })
    fireEvent.change(screen.getByLabelText('Estimated cost'), { target: { value: '45000' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Maintenance Work' }))
    await waitFor(() => expect(fleetService.decideInspection).toHaveBeenCalledWith('inspection-1', {
      decision: 'maintenance_required', notes: 'Brake system needs corrective work before dispatch.', maintenance_system: 'braking', issue_type: 'Brake fade under load', priority: 'high', estimated_cost: 45000,
    }))
  })
})
