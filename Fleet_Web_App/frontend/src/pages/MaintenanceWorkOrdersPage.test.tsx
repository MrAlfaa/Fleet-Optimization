import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetService } from '../services/fleetService'
import type { MaintenanceRecord, Vehicle } from '../types'
import { MaintenanceWorkOrdersPage } from './MaintenanceWorkOrdersPage'

vi.mock('../services/fleetService', () => ({ fleetService: { listMaintenanceRecords: vi.fn(), listVehicles: vi.fn(), approveMaintenance: vi.fn(), startMaintenance: vi.fn(), completeMaintenance: vi.fn(), cancelMaintenance: vi.fn() } }))
vi.mock('../services/authService', () => ({ authService: { getSession: () => ({ role: 'maintenance_manager', permissions: ['maintenance.manage'] }) } }))

const vehicle = { id: 'vehicle-1', registrationNumber: 'WP CAA-1208', vehicleCode: 'QA-EV-008' } as Vehicle
const records: MaintenanceRecord[] = [
  work('work-1', 'planned', 'Braking inspection'),
  work('work-2', 'in_progress', 'Battery cooling repair'),
  work('work-3', 'completed', 'Tire replacement'),
]
function work(id: string, status: NonNullable<MaintenanceRecord['workOrderStatus']>, issue: string): MaintenanceRecord { return { id, vehicleId: 'vehicle-1', date: 'Aug 29, 2026', vehicle: 'WP CAA-1208', partName: issue, maintenanceType: 'corrective', maintenanceSystem: status === 'in_progress' ? 'cooling_system' : 'braking', eventKind: 'corrective_repair', priority: 'high', service: issue, technician: 'Unassigned', cost: '-', costValue: 0, status: status === 'completed' ? 'Completed' : 'Pending Parts', serviceDate: '2026-08-29T09:00:00Z', issueType: issue, workOrderStatus: status, inspectionId: 'inspection-1', assessmentId: 'assessment-1', estimatedCost: 18000, actualCost: status === 'completed' ? 17000 : null, startedAt: status === 'in_progress' ? '2026-08-29T10:00:00Z' : null, completedAt: null, completionEvidence: status === 'completed' ? 'Completed' : null, cancellationReason: null, createdAt: '2026-08-28T08:00:00Z', updatedAt: '2026-08-29T10:00:00Z' } }

beforeEach(() => { vi.clearAllMocks(); vi.mocked(fleetService.listVehicles).mockResolvedValue([vehicle]); vi.mocked(fleetService.listMaintenanceRecords).mockResolvedValue(records); vi.mocked(fleetService.completeMaintenance).mockResolvedValue({ ...records[1], workOrderStatus: 'completed', completionEvidence: 'Cooling system repaired' }) })
afterEach(() => cleanup())

describe('MaintenanceWorkOrdersPage', () => {
  it('defaults to active work and keeps terminal work immutable', async () => {
    render(<MemoryRouter><MaintenanceWorkOrdersPage /></MemoryRouter>)
    expect((await screen.findAllByText('Braking inspection')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Battery cooling repair').length).toBeGreaterThan(0)
    expect(screen.queryByText('Tire replacement')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Work order status'), { target: { value: 'completed' } })
    fireEvent.click(screen.getByRole('button', { name: 'Open' }))
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Complete Work' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cancel Work' })).not.toBeInTheDocument()
  })

  it('completes the explicitly selected work order with required evidence and cost', async () => {
    render(<MemoryRouter><MaintenanceWorkOrdersPage /></MemoryRouter>)
    await screen.findAllByText('Battery cooling repair')
    const rows = screen.getAllByRole('row')
    const target = rows.find((row) => within(row).queryByText('Battery cooling repair'))!
    fireEvent.click(within(target).getByRole('button', { name: 'Open' }))
    fireEvent.click(screen.getByRole('button', { name: 'Complete Work' }))
    const dialog = screen.getByRole('heading', { name: 'Complete Work Order' }).closest('section')!
    fireEvent.change(within(dialog).getByLabelText('Actual cost'), { target: { value: '22000' } })
    fireEvent.change(within(dialog).getByLabelText('Completion evidence'), { target: { value: 'Cooling pump replaced and functional test passed.' } })
    fireEvent.click(within(dialog).getByRole('button', { name: 'Complete Work' }))
    await waitFor(() => expect(fleetService.completeMaintenance).toHaveBeenCalledWith('work-2', expect.objectContaining({ actual_cost: 22000, completion_evidence: 'Cooling pump replaced and functional test passed.' })))
  })

  it('requires a cancellation reason before calling the API', async () => {
    render(<MemoryRouter><MaintenanceWorkOrdersPage /></MemoryRouter>)
    await screen.findAllByText('Braking inspection')
    fireEvent.click(screen.getAllByRole('button', { name: 'Open' })[0])
    fireEvent.click(screen.getByRole('button', { name: 'Cancel Work' }))
    fireEvent.click(screen.getByRole('button', { name: 'Confirm Cancellation' }))
    expect(fleetService.cancelMaintenance).not.toHaveBeenCalled()
  })
})
