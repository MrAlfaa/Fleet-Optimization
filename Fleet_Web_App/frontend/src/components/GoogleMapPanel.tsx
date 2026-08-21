import { importLibrary, setOptions } from '@googlemaps/js-api-loader'
import clsx from 'clsx'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

declare global {
  interface Window {
    gm_authFailure?: () => void
  }
}

export interface MapPoint {
  latitude: number
  longitude: number
}

export interface GoogleMapMarker {
  id: string
  label: string
  title: string
  subtitle?: string
  position: MapPoint
  color?: string
}

export interface GoogleMapPolyline {
  id: string
  path: MapPoint[]
  color?: string
}

interface GoogleMapPanelProps {
  markers: GoogleMapMarker[]
  polylines?: GoogleMapPolyline[]
  center?: MapPoint
  zoom?: number
  className?: string
  children?: ReactNode
}

const mapsApiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined
const mapsAuthFailureEvent = 'fleetopt:google-maps-auth-failure'
let mapsConfigured = false
let mapsPromise: Promise<{
  core: google.maps.CoreLibrary
  maps: google.maps.MapsLibrary
  marker: google.maps.MarkerLibrary
}> | null = null

function loadGoogleMaps() {
  if (!mapsApiKey) {
    return Promise.reject(new Error('Google Maps API key is not configured'))
  }
  if (!mapsConfigured) {
    window.gm_authFailure = () => {
      window.dispatchEvent(new Event(mapsAuthFailureEvent))
    }
    setOptions({ key: mapsApiKey, v: 'weekly' })
    mapsConfigured = true
  }
  if (!mapsPromise) {
    mapsPromise = Promise.all([
      importLibrary('core'),
      importLibrary('maps'),
      importLibrary('marker'),
    ]).then(([core, maps, marker]) => ({ core, maps, marker }))
  }
  return mapsPromise
}

function isValidPoint(point: MapPoint | null | undefined): point is MapPoint {
  return Boolean(
    point &&
      Number.isFinite(point.latitude) &&
      Number.isFinite(point.longitude) &&
      Math.abs(point.latitude) <= 90 &&
      Math.abs(point.longitude) <= 180,
  )
}

export function GoogleMapPanel({ markers, polylines = [], center, zoom = 12, className, children }: GoogleMapPanelProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<google.maps.Map | null>(null)
  const markerRefs = useRef<google.maps.Marker[]>([])
  const polylineRefs = useRef<google.maps.Polyline[]>([])
  const infoRef = useRef<google.maps.InfoWindow | null>(null)
  const [status, setStatus] = useState<'loading' | 'ready' | 'fallback'>('loading')

  const validMarkers = useMemo(
    () => markers.filter((marker) => isValidPoint(marker.position)),
    [markers],
  )
  const validPolylines = useMemo(
    () => polylines
      .map((polyline) => ({ ...polyline, path: polyline.path.filter(isValidPoint) }))
      .filter((polyline) => polyline.path.length > 1),
    [polylines],
  )

  useEffect(() => {
    let cancelled = false

    const handleMapsAuthFailure = () => {
      if (!cancelled) {
        setStatus('fallback')
      }
    }

    window.addEventListener(mapsAuthFailureEvent, handleMapsAuthFailure)

    async function renderMap() {
      try {
        const googleLibraries = await loadGoogleMaps()
        if (cancelled || !containerRef.current) return

        const initialCenter = center && isValidPoint(center)
          ? center
          : validMarkers[0]?.position ?? validPolylines[0]?.path[0] ?? { latitude: 6.9271, longitude: 79.8612 }

        if (!mapRef.current) {
          mapRef.current = new googleLibraries.maps.Map(containerRef.current, {
            center: { lat: initialCenter.latitude, lng: initialCenter.longitude },
            zoom,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true,
            clickableIcons: false,
          })
          infoRef.current = new googleLibraries.maps.InfoWindow()
        }

        markerRefs.current.forEach((marker) => marker.setMap(null))
        polylineRefs.current.forEach((polyline) => polyline.setMap(null))
        markerRefs.current = []
        polylineRefs.current = []

        const bounds = new googleLibraries.core.LatLngBounds()
        let hasBounds = false

        validPolylines.forEach((polyline) => {
          const path = polyline.path.map((point) => ({ lat: point.latitude, lng: point.longitude }))
          path.forEach((point) => {
            bounds.extend(point)
            hasBounds = true
          })
          polylineRefs.current.push(new googleLibraries.maps.Polyline({
            map: mapRef.current,
            path,
            strokeColor: polyline.color ?? '#1D4ED8',
            strokeOpacity: 0.88,
            strokeWeight: 5,
          }))
        })

        validMarkers.forEach((marker) => {
          const position = { lat: marker.position.latitude, lng: marker.position.longitude }
          bounds.extend(position)
          hasBounds = true
          const googleMarker = new googleLibraries.marker.Marker({
            map: mapRef.current,
            position,
            title: marker.title,
            label: { text: marker.label, color: '#FFFFFF', fontWeight: '800' },
            icon: {
              path: googleLibraries.core.SymbolPath.CIRCLE,
              fillColor: marker.color ?? '#1D4ED8',
              fillOpacity: 1,
              scale: 13,
              strokeColor: '#FFFFFF',
              strokeWeight: 3,
            },
          })
          googleMarker.addListener('click', () => {
            const content = document.createElement('div')
            const title = document.createElement('strong')
            title.textContent = marker.title
            content.appendChild(title)
            if (marker.subtitle) {
              content.appendChild(document.createElement('br'))
              content.appendChild(document.createTextNode(marker.subtitle))
            }
            infoRef.current?.setContent(content)
            infoRef.current?.open({ anchor: googleMarker, map: mapRef.current })
          })
          markerRefs.current.push(googleMarker)
        })

        if (hasBounds) {
          mapRef.current.fitBounds(bounds, 64)
        } else {
          mapRef.current.setCenter({ lat: initialCenter.latitude, lng: initialCenter.longitude })
          mapRef.current.setZoom(zoom)
        }
        setStatus('ready')
      } catch {
        if (!cancelled) {
          setStatus('fallback')
        }
      }
    }

    void renderMap()
    return () => {
      cancelled = true
      window.removeEventListener(mapsAuthFailureEvent, handleMapsAuthFailure)
    }
  }, [center, validMarkers, validPolylines, zoom])

  if (status === 'fallback') {
    return (
      <div className={clsx('map-grid relative min-h-[360px] overflow-hidden rounded-lg border border-slate-300 bg-slate-100 shadow-inner', className)}>
        <div className="absolute inset-0 bg-slate-900/10" />
        <div className="absolute right-4 top-4 rounded-lg bg-white/95 px-3 py-2 text-xs font-semibold text-slate-600 shadow ring-1 ring-slate-200">
          Map tiles unavailable
        </div>
        {children}
      </div>
    )
  }

  return (
    <div className={clsx('relative min-h-[360px] overflow-hidden rounded-2xl border border-slate-300 shadow-inner', className)}>
      <div className="absolute inset-0" ref={containerRef} />
      {status === 'loading' && (
        <div className="absolute inset-0 grid place-items-center bg-slate-100 text-sm font-black text-fleet-muted">
          Loading Google Maps...
        </div>
      )}
      {children}
    </div>
  )
}
