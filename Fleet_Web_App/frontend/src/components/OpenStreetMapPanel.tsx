import clsx from 'clsx'
import { divIcon, latLngBounds } from 'leaflet'
import { House } from 'lucide-react'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { Circle, MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

export interface MapPoint {
  latitude: number
  longitude: number
}

export interface OpenStreetMapMarker {
  id: string
  label: string
  title: string
  subtitle?: string
  position: MapPoint
  color?: string
  kind?: 'default' | 'branch'
}

export interface OpenStreetMapCircle {
  id: string
  center: MapPoint
  radiusMeters: number
  color?: string
  fillColor?: string
  fillOpacity?: number
  title?: string
  subtitle?: string
}

export interface OpenStreetMapPolyline {
  id: string
  path: MapPoint[]
  color?: string
}

interface OpenStreetMapPanelProps {
  markers: OpenStreetMapMarker[]
  circles?: OpenStreetMapCircle[]
  polylines?: OpenStreetMapPolyline[]
  center?: MapPoint
  zoom?: number
  className?: string
  children?: ReactNode
  onMarkerSelect?: (marker: OpenStreetMapMarker) => void
  onCircleSelect?: (circle: OpenStreetMapCircle) => void
}

const DEFAULT_CENTER: MapPoint = { latitude: 6.9271, longitude: 79.8612 }
const TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const ATTRIBUTION = '&copy; OpenStreetMap contributors'

function isValidPoint(point: MapPoint | null | undefined): point is MapPoint {
  return Boolean(
    point &&
      Number.isFinite(point.latitude) &&
      Number.isFinite(point.longitude) &&
      Math.abs(point.latitude) <= 90 &&
      Math.abs(point.longitude) <= 180,
  )
}

function markerIcon(marker: OpenStreetMapMarker) {
  const label = marker.label.replace(/[<>&"']/g, '')
  const color = /^#[0-9a-f]{6}$/i.test(marker.color ?? '') ? marker.color : '#1D4ED8'
  const content = marker.kind === 'branch'
    ? renderToStaticMarkup(<House aria-hidden="true" color="white" size={18} strokeWidth={2.5} />)
    : label
  return divIcon({
    className: '',
    html: `<span class="fleet-map-marker" data-marker-kind="${marker.kind ?? 'default'}" style="background:${color}">${content}</span>`,
    iconAnchor: [17, 17],
    iconSize: [34, 34],
  })
}

export function OpenStreetMapPanel({
  markers,
  circles = [],
  polylines = [],
  center,
  zoom = 12,
  className,
  children,
  onMarkerSelect,
  onCircleSelect,
}: OpenStreetMapPanelProps) {
  const [tileStatus, setTileStatus] = useState<'loading' | 'ready' | 'failed'>('loading')
  const validMarkers = useMemo(() => markers.filter((marker) => isValidPoint(marker.position)), [markers])
  const validCircles = useMemo(
    () => circles.filter((circle) => isValidPoint(circle.center) && Number.isFinite(circle.radiusMeters) && circle.radiusMeters > 0),
    [circles],
  )
  const validPolylines = useMemo(
    () => polylines
      .map((polyline) => ({ ...polyline, path: polyline.path.filter(isValidPoint) }))
      .filter((polyline) => polyline.path.length > 1),
    [polylines],
  )
  const initialCenter = isValidPoint(center)
    ? center
    : validMarkers[0]?.position ?? validCircles[0]?.center ?? validPolylines[0]?.path[0] ?? DEFAULT_CENTER

  const boundsPoints = useMemo(() => [
    ...validMarkers.map((marker) => marker.position),
    ...validCircles.map((circle) => circle.center),
    ...validPolylines.flatMap((polyline) => polyline.path),
  ], [validCircles, validMarkers, validPolylines])

  return (
    <div
      aria-label="OpenStreetMap operational map"
      className={clsx('relative min-h-[360px] min-w-0 overflow-hidden rounded-lg border border-slate-300 bg-slate-100 shadow-inner', className)}
      role="region"
    >
      <MapContainer
        center={[initialCenter.latitude, initialCenter.longitude]}
        className="absolute inset-0 h-full w-full"
        scrollWheelZoom
        zoom={zoom}
        zoomControl
      >
        <TileLayer
          attribution={ATTRIBUTION}
          eventHandlers={{
            load: () => setTileStatus((current) => current === 'failed' ? current : 'ready'),
            tileerror: () => setTileStatus('failed'),
          }}
          url={TILE_URL}
        />
        <FitMapBounds center={initialCenter} points={boundsPoints} zoom={zoom} />
        {validPolylines.map((polyline) => (
          <Polyline
            key={polyline.id}
            pathOptions={{ color: polyline.color ?? '#1D4ED8', opacity: 0.88, weight: 5 }}
            positions={polyline.path.map((point) => [point.latitude, point.longitude])}
          />
        ))}
        {validCircles.map((circle) => (
          <Circle
            center={[circle.center.latitude, circle.center.longitude]}
            eventHandlers={{ click: () => onCircleSelect?.(circle) }}
            key={circle.id}
            pathOptions={{
              color: circle.color ?? '#0F766E',
              fillColor: circle.fillColor ?? circle.color ?? '#0F766E',
              fillOpacity: circle.fillOpacity ?? 0.14,
              weight: 2,
            }}
            radius={circle.radiusMeters}
          >
            {circle.title && <Popup><MapPopup subtitle={circle.subtitle} title={circle.title} /></Popup>}
          </Circle>
        ))}
        {validMarkers.map((marker) => (
          <Marker
            eventHandlers={{ click: () => onMarkerSelect?.(marker) }}
            icon={markerIcon(marker)}
            key={marker.id}
            position={[marker.position.latitude, marker.position.longitude]}
          >
            <Popup><MapPopup subtitle={marker.subtitle} title={marker.title} /></Popup>
          </Marker>
        ))}
      </MapContainer>
      {tileStatus === 'loading' && (
        <div className="pointer-events-none absolute inset-0 z-[400] grid place-items-center bg-slate-100/90 text-sm font-bold text-fleet-muted">
          Loading OpenStreetMap...
        </div>
      )}
      {tileStatus === 'failed' && (
        <div className="pointer-events-none absolute right-4 top-4 z-[500] rounded-lg bg-white/95 px-3 py-2 text-xs font-semibold text-slate-600 shadow ring-1 ring-slate-200">
          Map tiles unavailable
        </div>
      )}
      <div className="pointer-events-none absolute inset-0 z-[450] [&>*]:pointer-events-auto">{children}</div>
    </div>
  )
}

function FitMapBounds({ center, points, zoom }: { center: MapPoint; points: MapPoint[]; zoom: number }) {
  const map = useMap()

  useEffect(() => {
    map.invalidateSize()
    if (points.length > 1) {
      map.fitBounds(latLngBounds(points.map((point) => [point.latitude, point.longitude])), { padding: [44, 44], maxZoom: 15 })
      return
    }
    const nextCenter = points[0] ?? center
    map.setView([nextCenter.latitude, nextCenter.longitude], zoom)
  }, [center, map, points, zoom])

  return null
}

function MapPopup({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="min-w-40 py-1">
      <div className="font-bold text-slate-950">{title}</div>
      {subtitle && <div className="mt-1 text-xs leading-5 text-slate-600">{subtitle}</div>}
    </div>
  )
}
