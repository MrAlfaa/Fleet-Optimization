import { cleanup, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  TileLayer: ({ attribution }: { attribution: string }) => <div>{attribution}</div>,
  Marker: ({ children, draggable }: { children?: ReactNode; draggable?: boolean }) => <div data-draggable={String(Boolean(draggable))}>{children}</div>,
  Popup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  useMapEvents: () => null,
}))

vi.mock('leaflet', () => ({
  divIcon: (options: unknown) => options,
}))

import { DeliveryLocationPicker } from './DeliveryLocationPicker'

const branch = {
  id: 'colombo_central_branch', name: 'Colombo Central Branch', address: 'Colombo, Sri Lanka',
  latitude: 6.9271, longitude: 79.8612, timezone: 'Asia/Colombo', deliveryPeriods: [],
}

describe('DeliveryLocationPicker', () => {
  afterEach(cleanup)

  it('keeps the branch fixed and only allows the delivery point to be selected', () => {
    render(<DeliveryLocationPicker branch={branch} drop={null} onDropChange={vi.fn()} />)

    expect(screen.getAllByText('Colombo Central Branch')).toHaveLength(2)
    expect(screen.getByText(/fixed parcel origin/i)).toBeInTheDocument()
    expect(screen.getByText(/click the map to set the customer delivery location/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /pickup/i })).not.toBeInTheDocument()
  })
})
