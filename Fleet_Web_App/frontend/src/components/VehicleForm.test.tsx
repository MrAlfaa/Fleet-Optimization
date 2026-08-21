import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { VehicleForm } from './VehicleForm'


describe('VehicleForm', () => {
  it('presents a sectioned EV workflow without implementation-facing labels', () => {
    render(<VehicleForm onCancel={vi.fn()} onCreated={vi.fn()} />)

    expect(screen.getByRole('heading', { name: 'Vehicle identity' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'EV specifications' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Operational state' })).toBeInTheDocument()
    expect(screen.getByLabelText('Vehicle image')).toHaveAttribute('accept', 'image/jpeg,image/png,image/webp')
    expect(screen.queryByText(/Backend API/i)).not.toBeInTheDocument()
  })
})
