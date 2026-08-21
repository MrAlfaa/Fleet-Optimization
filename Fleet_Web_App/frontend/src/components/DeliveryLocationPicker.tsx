import { divIcon, type LeafletMouseEvent, type Marker as LeafletMarker } from 'leaflet'
import { MapPin, Navigation, Warehouse } from 'lucide-react'
import { MapContainer, Marker, TileLayer, useMapEvents } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import type { LocationPoint } from '../utils/operationalZones'

type Mode = 'pickup' | 'drop'

interface Props {
  pickup: LocationPoint | null
  drop: LocationPoint | null
  mode: Mode
  onModeChange: (mode: Mode) => void
  onPickupChange: (point: LocationPoint) => void
  onDropChange: (point: LocationPoint) => void
}

const pickupIcon = divIcon({ className: '', html: '<div class="fleet-map-marker fleet-map-marker-pickup">P</div>', iconSize: [34, 34], iconAnchor: [17, 17] })
const dropIcon = divIcon({ className: '', html: '<div class="fleet-map-marker fleet-map-marker-drop">D</div>', iconSize: [34, 34], iconAnchor: [17, 17] })

export function DeliveryLocationPicker({ pickup, drop, mode, onModeChange, onPickupChange, onDropChange }: Props) {
  const selectPoint = (point: LocationPoint) => mode === 'pickup' ? onPickupChange(point) : onDropChange(point)
  return <div className="overflow-hidden rounded-xl border border-fleet-line bg-slate-50">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-fleet-line bg-white p-3">
      <div><div className="font-bold text-fleet-ink">Select locations on map</div><div className="text-xs text-fleet-muted">Click or drag a marker. P = pickup, D = drop.</div></div>
      <div className="inline-flex rounded-lg border border-fleet-line bg-slate-50 p-1">
        <button className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-xs font-bold ${mode === 'pickup' ? 'bg-fleet-blue text-white' : 'text-fleet-muted'}`} onClick={() => onModeChange('pickup')} type="button"><Warehouse className="h-4 w-4" />Pickup</button>
        <button className={`inline-flex items-center gap-2 rounded-md px-3 py-2 text-xs font-bold ${mode === 'drop' ? 'bg-fleet-blue text-white' : 'text-fleet-muted'}`} onClick={() => onModeChange('drop')} type="button"><MapPin className="h-4 w-4" />Drop</button>
      </div>
    </div>
    <MapContainer center={[6.9271, 79.8612]} className="h-[360px] w-full" scrollWheelZoom zoom={11}>
      <TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <ClickHandler onSelect={selectPoint} />
      {pickup && <DraggablePoint icon={pickupIcon} point={pickup} onChange={onPickupChange} />}
      {drop && <DraggablePoint icon={dropIcon} point={drop} onChange={onDropChange} />}
    </MapContainer>
    <div className="grid gap-2 border-t border-fleet-line bg-white p-3 sm:grid-cols-2">
      <Coordinate label="Pickup" point={pickup} />
      <Coordinate label="Drop" point={drop} />
    </div>
  </div>
}

function ClickHandler({ onSelect }: { onSelect: (point: LocationPoint) => void }) {
  useMapEvents({ click: (event: LeafletMouseEvent) => onSelect({ latitude: event.latlng.lat, longitude: event.latlng.lng }) })
  return null
}

function DraggablePoint({ icon, point, onChange }: { icon: ReturnType<typeof divIcon>; point: LocationPoint; onChange: (point: LocationPoint) => void }) {
  return <Marker draggable eventHandlers={{ dragend: (event) => { const value = (event.target as LeafletMarker).getLatLng(); onChange({ latitude: value.lat, longitude: value.lng }) } }} icon={icon} position={[point.latitude, point.longitude]} />
}

function Coordinate({ label, point }: { label: string; point: LocationPoint | null }) {
  return <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs"><Navigation className="h-4 w-4 text-fleet-blue" /><span className="font-bold">{label}</span><span className="ml-auto font-mono text-fleet-muted">{point ? `${point.latitude.toFixed(5)}, ${point.longitude.toFixed(5)}` : 'Not selected'}</span></div>
}
