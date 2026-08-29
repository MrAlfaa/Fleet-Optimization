import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetService } from '../services/fleetService'
import type { Vehicle, VehicleMaintenanceInspection } from '../types'
import { InspectionWorkspacePage } from './InspectionWorkspacePage'

vi.mock('../services/fleetService', () => ({ fleetService: {
  getInspection: vi.fn(), getVehicle: vi.fn(), startInspection: vi.fn(), saveInspectionDraft: vi.fn(), completeInspection: vi.fn(),
} }))
vi.mock('../services/authService', () => ({ authService: { getSession: () => ({ id: 'user-1', role: 'maintenance_manager', permissions: ['maintenance.manage'] }) } }))

const vehicle = { id: 'vehicle-1', registrationNumber: 'WP CAA-1208', vehicleCode: 'QA-EV-008', model: 'BYD T3' } as Vehicle
const baseInspection = {
  id: 'inspection-1', vehicleId: 'vehicle-1', assessmentId: 'assessment-1', featureHash: 'hash-1', status: 'in_progress', isActive: true,
  priority: 'high', inspectionAreas: ['Braking', 'Tires'], notes: null, checklist: [], summary: null,
  draftChecklist: [{ key: 'braking', label: 'Braking', outcome: 'failed', remark: 'Pedal travel is excessive' }],
  draftSummary: 'Brake inspection underway', draftSavedBy: 'user-1', draftSavedAt: '2026-08-27T08:20:00Z',
  assignedTo: 'user-1', assignedBy: 'admin-1', assignedAt: '2026-08-27T08:00:00Z', startedBy: 'user-1', startedAt: '2026-08-27T08:10:00Z',
  completedBy: null, completedAt: null, decision: null, decisionNotes: null, decidedBy: null, decidedAt: null, workOrderId: null,
  cancellationReason: null, createdBy: 'admin-1', createdAt: '2026-08-27T07:00:00Z', updatedAt: '2026-08-27T08:20:00Z',
} as VehicleMaintenanceInspection

function renderPage() {
  return render(<MemoryRouter initialEntries={['/maintenance/inspections/inspection-1']}><Routes><Route path="/maintenance/inspections/:inspectionId" element={<InspectionWorkspacePage />} /><Route path="/maintenance/inspections/:inspectionId/decision" element={<div>Decision destination</div>} /></Routes></MemoryRouter>)
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true })
  vi.setSystemTime(new Date('2026-08-27T09:10:00Z'))
  vi.mocked(fleetService.getVehicle).mockResolvedValue(vehicle)
  vi.mocked(fleetService.getInspection).mockResolvedValue(baseInspection)
  vi.mocked(fleetService.saveInspectionDraft).mockResolvedValue(baseInspection)
})
afterEach(() => { cleanup(); vi.clearAllMocks(); vi.useRealTimers() })

describe('InspectionWorkspacePage', () => {
  it('restores the persisted server draft and saves the backend payload', async () => {
    renderPage()
    expect(await screen.findByDisplayValue('Pedal travel is excessive')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Brake inspection underway')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Save draft' }))
    await waitFor(() => expect(fleetService.saveInspectionDraft).toHaveBeenCalledWith('inspection-1', {
      checklist: [{ key: 'braking', label: 'Braking', outcome: 'failed', remark: 'Pedal travel is excessive' }],
      summary: 'Brake inspection underway',
    }))
  })

  it('shows elapsed time derived from the persisted server start timestamp', async () => {
    renderPage()
    expect(await screen.findByText('01:00:00')).toBeInTheDocument()
    await vi.advanceTimersByTimeAsync(1000)
    expect(await screen.findByText('01:00:01')).toBeInTheDocument()
  })

  it('keeps terminal inspection evidence read-only', async () => {
    vi.mocked(fleetService.getInspection).mockResolvedValue({ ...baseInspection, status: 'returned_to_service', isActive: false, checklist: [{ key: 'braking', label: 'Braking', outcome: 'passed', remark: null }], summary: 'Vehicle cleared' })
    renderPage()
    expect(await screen.findByText('Vehicle cleared')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Save draft' })).not.toBeInTheDocument()
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
  })
})
