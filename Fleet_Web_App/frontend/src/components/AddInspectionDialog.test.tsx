import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { fleetService } from '../services/fleetService'
import type { MaintenancePrediction, Vehicle } from '../types'
import { AddInspectionDialog } from './AddInspectionDialog'

vi.mock('../services/fleetService', () => ({ fleetService: { createInspection: vi.fn() } }))
const vehicle = { id: 'vehicle-1', registrationNumber: 'WP CAA-1208' } as Vehicle
const assessment = { id: 'assessment-1', featureHash: 'feature-hash-1', risk: 'high', systemRisks: [{ key: 'braking', name: 'Braking', probability: 0.42, risk: 'high' }] } as MaintenancePrediction
afterEach(() => { cleanup(); vi.clearAllMocks() })

describe('AddInspectionDialog', () => {
  it('submits only the assessment identity and confirmed operational scope', async () => {
    vi.mocked(fleetService.createInspection).mockResolvedValue({ id: 'inspection-1' } as never)
    const created = vi.fn()
    render(<AddInspectionDialog assessment={assessment} onClose={vi.fn()} onCreated={created} vehicle={vehicle} />)
    fireEvent.change(screen.getByLabelText('Operational note (optional)'), { target: { value: 'Driver reported braking noise' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add to inspection' }))
    await waitFor(() => expect(fleetService.createInspection).toHaveBeenCalledWith({
      vehicle_id: 'vehicle-1', assessment_id: 'assessment-1', feature_hash: 'feature-hash-1', priority: 'high', inspection_areas: ['Braking'], notes: 'Driver reported braking noise',
    }))
    expect(created).toHaveBeenCalled()
  })
})
