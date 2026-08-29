import { divIcon, type LeafletMouseEvent, type Marker as LeafletMarker } from 'leaflet'
import { House, MapPin } from 'lucide-react'
import { renderToStaticMarkup } from 'react-dom/server'
import { MapContainer, Marker, Popup, TileLayer, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { OperationalBranch } from '../types'
import type { LocationPoint } from '../utils/operationalZones'

interface Props {
  branch: OperationalBranch
  drop: LocationPoint | null
  onDropChange: (point: LocationPoint) => void
}

const branchIcon = divIcon({
  className: '',
  html: `<div class="fleet-map-marker fleet-map-marker-pickup">${renderToStaticMarkup(<House aria-hidden="true" color="white" size={18} strokeWidth={2.5} />)}</div>`,
  iconSize: [34, 34],
  iconAnchor: [17, 17],
})
const dropIcon = divIcon({ className: '', html: '<div class="fleet-map-marker fleet-map-marker-drop">D</div>', iconSize: [34, 34], iconAnchor: [17, 17] })

export function DeliveryLocationPicker({ branch, drop, onDropChange }: Props) {
  return <div className="overflow-hidden rounded-xl border border-fleet-line bg-slate-50">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-fleet-line bg-white p-3">
      <div>
        <div className="font-bold text-fleet-ink">Set customer delivery location</div>
        <div className="text-xs text-fleet-muted">Click the map to set the customer delivery location, then drag the marker to refine it.</div>
      </div>
      <div className="inline-flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-bold text-emerald-800">
        <House className="h-4 w-4" />Fixed parcel origin
      </div>
    </div>
    <MapContainer center={[branch.latitude, branch.longitude]} className="h-[360px] w-full" scrollWheelZoom zoom={11}>
      <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <ClickHandler onSelect={onDropChange} />
      <Marker icon={branchIcon} position={[branch.latitude, branch.longitude]}>
        <Popup><div className="min-w-44"><strong>{branch.name}</strong><div className="mt-1 text-xs text-slate-600">{branch.address}</div><div className="mt-2 text-xs font-semibold text-emerald-700">All parcels leave from this branch.</div></div></Popup>
      </Marker>
      {drop && <DraggablePoint point={drop} onChange={onDropChange} />}
    </MapContainer>
    <div className="grid gap-2 border-t border-fleet-line bg-white p-3 sm:grid-cols-2">
      <Coordinate icon="branch" label={branch.name} point={{ latitude: branch.latitude, longitude: branch.longitude }} />
      <Coordinate icon="drop" label="Customer delivery" point={drop} />
    </div>
  </div>
}

function ClickHandler({ onSelect }: { onSelect: (point: LocationPoint) => void }) {
  useMapEvents({ click: (event: LeafletMouseEvent) => onSelect({ latitude: event.latlng.lat, longitude: event.latlng.lng }) })
  return null
}

function DraggablePoint({ point, onChange }: { point: LocationPoint; onChange: (point: LocationPoint) => void }) {
  return <Marker draggable eventHandlers={{ dragend: (event) => { const value = (event.target as LeafletMarker).getLatLng(); onChange({ latitude: value.lat, longitude: value.lng }) } }} icon={dropIcon} position={[point.latitude, point.longitude]} />
}

function Coordinate({ icon, label, point }: { icon: 'branch' | 'drop'; label: string; point: LocationPoint | null }) {
  const Icon = icon === 'branch' ? House : MapPin
  return <div className="flex min-w-0 items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs"><Icon className="h-4 w-4 shrink-0 text-fleet-blue" /><span className="truncate font-bold">{label}</span><span className="ml-auto shrink-0 font-mono text-fleet-muted">{point ? `${point.latitude.toFixed(5)}, ${point.longitude.toFixed(5)}` : 'Not selected'}</span></div>
}
