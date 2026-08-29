import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Vehicle } from '../types'
import { MaintenanceRecordDialog } from './MaintenanceRecordDialog'
import { fleetService } from '../services/fleetService'

const vehicle: Vehicle = {
  id: 'vehicle-1', number: 'WP CAA-1234', registrationNumber: 'WP CAA-1234', vehicleCode: 'FLEET-1',
  imageUrl: null, category: 'Van', vehicleCategory: 'van', fuelType: 'electric', model: 'BYD T3', type: 'electric_van',
  assignedDriver: 'Unassigned', mileage: 12000, status: 'Active', risk: 'low',
}

describe('MaintenanceRecordDialog', () => {
  it('uses controlled maintenance system and event-kind fields', () => {
    render(<MaintenanceRecordDialog onClose={vi.fn()} onSaved={vi.fn()} vehicle={vehicle} />)

    expect(screen.getByLabelText('Maintenance system')).toBeInTheDocument()
    expect(screen.getByLabelText('Event kind')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Corrective Repair' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Breakdown' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Battery System' })).toHaveValue('battery_system')
    expect(screen.getByRole('option', { name: 'Motor Drivetrain' })).toHaveValue('motor_drivetrain')
    expect(screen.queryByRole('option', { name: 'Battery Cooling' })).not.toBeInTheDocument()
  })

  it('shows when new work is linked to an engineering review', () => {
    render(<MaintenanceRecordDialog onClose={vi.fn()} onSaved={vi.fn()} predictionReviewId="review-1" vehicle={vehicle} />)
    expect(screen.getByText(/linked engineering review/i)).toBeInTheDocument()
  })

  it('submits the linked prediction review identifier', async () => {
    const create = vi.spyOn(fleetService, 'createMaintenanceRecord').mockResolvedValue({} as never)
    const view = render(<MaintenanceRecordDialog onClose={vi.fn()} onSaved={vi.fn()} predictionReviewId="review-1" vehicle={vehicle} />)
    const dialog = within(view.container)
    fireEvent.change(dialog.getByLabelText('Part'), { target: { value: 'Brake Pads' } })
    fireEvent.change(dialog.getByLabelText('Issue / service description'), { target: { value: 'Inspect braking system' } })
    fireEvent.change(dialog.getByLabelText('Technician'), { target: { value: 'Engineer' } })
    fireEvent.change(dialog.getByLabelText('Cost'), { target: { value: '0' } })
    fireEvent.submit(dialog.getByRole('button', { name: 'Save record' }).closest('form')!)

    await waitFor(() => expect(create).toHaveBeenCalledWith(expect.objectContaining({ prediction_review_id: 'review-1', vehicle_id: 'vehicle-1' })))
    create.mockRestore()
  })
})
