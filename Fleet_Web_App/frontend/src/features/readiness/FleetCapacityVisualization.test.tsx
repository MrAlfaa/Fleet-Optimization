import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { FleetCapacityVisualization } from './FleetCapacityVisualization'

describe('FleetCapacityVisualization', () => {
  beforeEach(() => {
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
  })

  it('keeps the complete capacity decision available in semantic HTML', () => {
    render(
      <FleetCapacityVisualization
        readiness={{
          requiredVehicles: 12,
          eligibleVehicles: 9,
          warningVehicles: 2,
          blockedVehicles: 3,
        }}
      />,
    )

    expect(screen.getByRole('region', { name: 'Dispatch capacity deck' })).toBeInTheDocument()
    expect(screen.getByText('9 of 12 required vehicles are available for dispatch.')).toBeInTheDocument()
    expect(screen.getByText('Capacity shortage: 3 vehicles.')).toBeInTheDocument()
    expect(screen.getByText('7 ready')).toBeInTheDocument()
    expect(screen.getByText('2 available with warnings')).toBeInTheDocument()
    expect(screen.getByText('3 blocked')).toBeInTheDocument()
  })

  it('shows a stable loading placeholder before the lazy scene resolves', () => {
    render(
      <FleetCapacityVisualization
        readiness={{
          requiredVehicles: 6,
          eligibleVehicles: 6,
          warningVehicles: 1,
          blockedVehicles: 0,
        }}
      />,
    )

    expect(screen.getByTestId('capacity-scene-loading')).toBeInTheDocument()
  })

  it('replaces the canvas with an equivalent CSS deck when WebGL is unavailable', async () => {
    render(
      <FleetCapacityVisualization
        readiness={{
          requiredVehicles: 5,
          eligibleVehicles: 3,
          warningVehicles: 1,
          blockedVehicles: 2,
        }}
      />,
    )

    await waitFor(() => {
      expect(screen.getByTestId('capacity-css-fallback')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('capacity-three-scene')).not.toBeInTheDocument()
  })
})
