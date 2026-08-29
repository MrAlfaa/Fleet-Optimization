import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ReactNode } from 'react'

const fitBounds = vi.fn()
const setView = vi.fn()
const invalidateSize = vi.fn()

vi.mock('react-leaflet', () => ({
  MapContainer: ({ children, className }: { children: ReactNode; className?: string }) => <div className={className} data-testid="leaflet-map">{children}</div>,
  TileLayer: ({ attribution, eventHandlers }: { attribution: string; eventHandlers?: { load?: () => void; tileerror?: () => void } }) => (
    <div data-testid="tile-layer">
      <span>{attribution}</span>
      <button onClick={eventHandlers?.load} type="button">load tiles</button>
      <button onClick={eventHandlers?.tileerror} type="button">fail tiles</button>
    </div>
  ),
  Marker: ({ children, icon, position }: { children?: ReactNode; icon?: { html?: string }; position: [number, number] }) => <div data-position={position.join(',')} data-testid="map-marker"><span dangerouslySetInnerHTML={{ __html: icon?.html ?? '' }} />{children}</div>,
  Popup: ({ children }: { children: ReactNode }) => <div>{children}</div>,
  Circle: ({ center }: { center: [number, number] }) => <div data-center={center.join(',')} data-testid="map-circle" />,
  Polyline: ({ positions }: { positions: [number, number][] }) => <div data-points={positions.length} data-testid="map-polyline" />,
  useMap: () => ({ fitBounds, invalidateSize, setView }),
}))

vi.mock('leaflet', () => ({
  divIcon: (options: unknown) => options,
  latLngBounds: (points: unknown) => ({ points, isValid: () => true }),
}))

import { OpenStreetMapPanel } from './OpenStreetMapPanel'

describe('OpenStreetMapPanel', () => {
  afterEach(cleanup)

  beforeEach(() => {
    fitBounds.mockClear()
    invalidateSize.mockClear()
    setView.mockClear()
  })

  it('renders valid markers, circles, polylines, popups, and OSM attribution', () => {
    render(
      <OpenStreetMapPanel
        circles={[{ id: 'service-area', center: { latitude: 6.9271, longitude: 79.8612 }, radiusMeters: 5000 }]}
        markers={[
          { id: 'valid', label: '1', title: 'Colombo Central', subtitle: '12 active deliveries', position: { latitude: 6.9271, longitude: 79.8612 } },
          { id: 'invalid', label: '2', title: 'Invalid', position: { latitude: 100, longitude: 79.8 } },
        ]}
        polylines={[{ id: 'route', path: [{ latitude: 6.9271, longitude: 79.8612 }, { latitude: 6.8649, longitude: 79.8997 }] }]}
      />,
    )

    expect(screen.getAllByTestId('map-marker')).toHaveLength(1)
    expect(screen.getByTestId('map-circle')).toBeInTheDocument()
    expect(screen.getByTestId('map-polyline')).toHaveAttribute('data-points', '2')
    expect(screen.getByText('Colombo Central')).toBeInTheDocument()
    expect(screen.getByText('12 active deliveries')).toBeInTheDocument()
    expect(screen.getByText(/OpenStreetMap contributors/i)).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'OpenStreetMap operational map' })).toBeInTheDocument()
    expect(fitBounds).toHaveBeenCalled()
  })

  it('contains tile failures and keeps overlay content usable', () => {
    render(
      <OpenStreetMapPanel markers={[]}>
        <div>Live trip summary</div>
      </OpenStreetMapPanel>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'fail tiles' }))
    fireEvent.click(screen.getByRole('button', { name: 'load tiles' }))

    expect(screen.getByText('Map tiles unavailable')).toBeInTheDocument()
    expect(screen.getByText('Live trip summary')).toBeInTheDocument()
    expect(screen.getByText(/OpenStreetMap contributors/i)).toBeInTheDocument()
  })

  it('renders the Colombo branch with a home marker', () => {
    const { container } = render(
      <OpenStreetMapPanel markers={[{
        id: 'branch', kind: 'branch', label: 'H', title: 'Colombo Central Branch',
        position: { latitude: 6.9271, longitude: 79.8612 },
      }]} />,
    )

    expect(container.querySelector('[data-marker-kind="branch"]')).toBeInTheDocument()
    expect(screen.getByText('Colombo Central Branch')).toBeInTheDocument()
  })
})
