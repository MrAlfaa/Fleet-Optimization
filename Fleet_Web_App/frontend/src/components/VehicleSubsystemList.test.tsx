import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { VehiclePart } from '../types'
import { VehicleSubsystemList } from './VehicleSubsystemList'


const parts: VehiclePart[] = [
  {
    id: 'battery',
    vehicleId: 'vehicle-1',
    name: 'Battery Pack',
    lastService: 'Aug 10, 2026',
    failures: 0,
    risk: 'high',
    riskScore: 62,
    status: 'warning',
    predictedNext: 'Sep 2, 2026',
    note: 'Inspection required',
  },
]


describe('VehicleSubsystemList', () => {
  it('renders scan-friendly subsystem risk and selection', () => {
    const onSelectPart = vi.fn()
    render(<VehicleSubsystemList onSelectPart={onSelectPart} parts={parts} />)

    expect(screen.getByText('Battery Pack')).toBeInTheDocument()
    expect(screen.getByLabelText('Battery Pack risk score 62 percent')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('subsystem-battery-pack'))
    expect(onSelectPart).toHaveBeenCalledWith(parts[0])
  })
})
