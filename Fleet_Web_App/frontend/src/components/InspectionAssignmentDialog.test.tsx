import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { fleetService } from '../services/fleetService'
import type { VehicleMaintenanceInspection } from '../types'
import { InspectionAssignmentDialog } from './InspectionAssignmentDialog'

vi.mock('../services/fleetService', () => ({ fleetService: { listInspectionAssignees: vi.fn(), assignInspection: vi.fn() } }))
const inspection = { id: 'inspection-1', status: 'pending', priority: 'high' } as VehicleMaintenanceInspection

afterEach(() => { cleanup(); vi.clearAllMocks() })

describe('InspectionAssignmentDialog', () => {
  it('submits the safe assignee id and optional note for authorized users', async () => {
    vi.mocked(fleetService.listInspectionAssignees).mockResolvedValue([{ id: 'user-1', fullName: 'M. Perera', role: 'maintenance_manager' }])
    vi.mocked(fleetService.assignInspection).mockResolvedValue({ ...inspection, assignedTo: 'user-1' })
    const assigned = vi.fn()
    render(<InspectionAssignmentDialog canManage inspection={inspection} onAssigned={assigned} onClose={vi.fn()} />)
    await screen.findByRole('option', { name: /M. Perera/ })
    fireEvent.change(screen.getByLabelText('Assignment note (optional)'), { target: { value: 'Inspect before next dispatch' } })
    fireEvent.click(screen.getByRole('button', { name: 'Assign inspection' }))
    await waitFor(() => expect(fleetService.assignInspection).toHaveBeenCalledWith('inspection-1', { assigned_to: 'user-1', notes: 'Inspect before next dispatch' }))
    expect(assigned).toHaveBeenCalled()
  })

  it('does not expose mutation controls to a read-only user', () => {
    render(<InspectionAssignmentDialog canManage={false} inspection={inspection} onAssigned={vi.fn()} onClose={vi.fn()} />)
    expect(screen.getByRole('alert')).toHaveTextContent(/view this inspection/i)
    expect(screen.queryByRole('button', { name: 'Assign inspection' })).not.toBeInTheDocument()
    expect(fleetService.listInspectionAssignees).not.toHaveBeenCalled()
  })
})
