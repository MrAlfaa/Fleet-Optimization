import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { VehicleForm } from './VehicleForm'
import { fleetService } from '../services/fleetService'
import type { Vehicle } from '../types'

vi.mock('../services/fleetService', () => ({
  fleetService: {
    createVehicle: vi.fn(), updateVehicle: vi.fn(), uploadVehicleImage: vi.fn(), deleteVehicleImage: vi.fn(),
  },
}))

const createdVehicle = {
  id: 'vehicle-1', number: 'WP CAA-1000', registrationNumber: 'WP CAA-1000', vehicleCode: 'FLT-001',
  imageUrl: null, category: 'Van', vehicleCategory: 'van', fuelType: 'electric', model: 'BYD T3', type: 'electric_van',
  assignedDriver: 'Unassigned', mileage: 0, status: 'Offline', risk: 'low',
} as Vehicle


describe('VehicleForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fleetService.createVehicle).mockResolvedValue(createdVehicle)
  })

  afterEach(cleanup)

  it('collects canonical multi-powertrain vehicle fields without implementation-facing labels', () => {
    render(<VehicleForm onCancel={vi.fn()} onCreated={vi.fn()} />)

    expect(screen.getByRole('heading', { name: 'Vehicle identity' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Fleet specifications' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Load capacity' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Operational state' })).toBeInTheDocument()
    expect(screen.getByLabelText('Vehicle category')).toBeInTheDocument()
    expect(screen.getByLabelText('Fuel type')).toBeInTheDocument()
    expect(screen.getByLabelText('In-service date')).toBeInTheDocument()
    expect(screen.getByLabelText('Payload capacity (kg)')).toBeInTheDocument()
    expect(screen.getByLabelText('Load profile')).toBeInTheDocument()
    expect(screen.getByText('Calculated cargo volume')).toBeInTheDocument()
    expect(screen.getByLabelText('Cargo length (cm)')).toBeInTheDocument()
    expect(screen.getByLabelText('Maximum parcels')).toBeInTheDocument()
    expect(screen.getByLabelText('Vehicle history type')).toBeInTheDocument()
    expect(screen.getByLabelText('Vehicle image')).toHaveAttribute('accept', 'image/jpeg,image/png,image/webp')
    expect(screen.queryByText(/Backend API/i)).not.toBeInTheDocument()
  })

  it('hides battery capacity for diesel vehicles while keeping history fields required', () => {
    const view = render(<VehicleForm onCancel={vi.fn()} onCreated={vi.fn()} />)
    const form = within(view.container)
    fireEvent.change(form.getByLabelText('Fuel type'), { target: { value: 'diesel' } })

    expect(form.queryByLabelText('Battery capacity (kWh, optional)')).not.toBeInTheDocument()
    expect(form.getByLabelText('In-service date')).toBeRequired()
    expect(form.getByLabelText('Payload capacity (kg)')).toBeRequired()
  })

  it('creates new vehicles inactive until operational review without changing edit behavior', async () => {
    const view = render(<VehicleForm onCancel={vi.fn()} onCreated={vi.fn()} />)
    fireEvent.submit(view.container.querySelector('form')!)

    await waitFor(() => expect(fleetService.createVehicle).toHaveBeenCalled())
    expect(fleetService.createVehicle).toHaveBeenCalledWith(expect.objectContaining({
      status: 'inactive', health_status: 'unknown', onboarding_type: 'existing_fleet',
      load_profile: expect.objectContaining({ profile_code: 'MEDIUM_VAN', capacity_m3: 9.52 }),
    }))
    expect(screen.getByText('Inactive - review required')).toBeInTheDocument()
  })

  it('applies category-specific internal cargo bay dimensions', () => {
    render(<VehicleForm onCancel={vi.fn()} onCreated={vi.fn()} />)

    fireEvent.change(screen.getByLabelText('Vehicle category'), { target: { value: 'truck' } })

    expect(screen.getByLabelText('Cargo length (cm)')).toHaveValue(540)
    expect(screen.getByLabelText('Cargo width (cm)')).toHaveValue(220)
    expect(screen.getByLabelText('Cargo height (cm)')).toHaveValue(210)
    expect(screen.getByText('24.948 m³')).toBeInTheDocument()
  })
})
