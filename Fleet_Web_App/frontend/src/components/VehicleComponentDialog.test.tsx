import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { fleetService } from '../services/fleetService'
import type { VehiclePart } from '../types'
import { VehicleComponentDialog } from './VehicleComponentDialog'

const archivedPart: VehiclePart = {
  id: 'part-1', vehicleId: 'vehicle-1', name: 'Battery Pack', category: 'battery',
  lastService: 'No service record', failures: 0, risk: 'low', riskScore: 0,
  status: 'unknown', predictedNext: 'No prediction', note: '', isActive: false,
}

describe('VehicleComponentDialog', () => {
  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('restores an archived catalogue part instead of creating a duplicate', async () => {
    vi.spyOn(fleetService, 'getEvPartCatalog').mockResolvedValue([{ key: 'battery_pack', name: 'Battery Pack', category: 'battery', description: 'Battery', mlSupported: true, mlSignalGroup: 'battery' }])
    const restore = vi.spyOn(fleetService, 'restoreVehiclePart').mockResolvedValue(archivedPart)
    const create = vi.spyOn(fleetService, 'createVehiclePart')

    render(<VehicleComponentDialog onClose={vi.fn()} onSaved={vi.fn()} parts={[archivedPart]} vehicleId="vehicle-1" />)

    fireEvent.change(await screen.findByLabelText('EV part'), { target: { value: 'battery_pack' } })
    fireEvent.click(screen.getByRole('button', { name: 'Restore part' }))

    await waitFor(() => expect(restore).toHaveBeenCalledWith('part-1'))
    expect(create).not.toHaveBeenCalled()
  })

  it('shows controlled custom fields only for Other part', async () => {
    vi.spyOn(fleetService, 'getEvPartCatalog').mockResolvedValue([])
    render(<VehicleComponentDialog onClose={vi.fn()} onSaved={vi.fn()} parts={[]} vehicleId="vehicle-1" />)

    expect(screen.queryByLabelText('Custom part name')).not.toBeInTheDocument()
    fireEvent.change(await screen.findByLabelText('EV part'), { target: { value: 'other' } })

    expect(screen.getByLabelText('Custom part name')).toBeInTheDocument()
    expect(screen.getByText(/not directly evaluated by the current ML model/i)).toBeInTheDocument()
  })

  it('confirms a soft delete and archives the selected part', async () => {
    vi.spyOn(fleetService, 'getEvPartCatalog').mockResolvedValue([])
    const archive = vi.spyOn(fleetService, 'archiveVehiclePart').mockResolvedValue({ ...archivedPart, isActive: false })
    const onSaved = vi.fn()

    render(<VehicleComponentDialog onClose={vi.fn()} onSaved={onSaved} part={{ ...archivedPart, isActive: true }} parts={[]} vehicleId="vehicle-1" />)

    fireEvent.click(await screen.findByRole('button', { name: 'Delete part' }))
    expect(screen.getByText(/maintenance and prediction history will be preserved/i)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Confirm delete' }))

    await waitFor(() => expect(archive).toHaveBeenCalledWith('part-1', 'Deleted from vehicle workspace'))
    expect(onSaved).toHaveBeenCalled()
  })
})
