import type { OpenStreetMapMarker, OpenStreetMapPolyline } from '../../components/OpenStreetMapPanel'
import type { LoadParcelPoint, ParetoOption } from './types'

const LOAD_COLORS = ['#2563eb', '#059669', '#d97706', '#7c3aed']

export interface CandidateRoutePreview {
  dropMarkers: OpenStreetMapMarker[]
  polylines: OpenStreetMapPolyline[]
}

export function buildCandidateRoutePreview(option: ParetoOption | null | undefined, parcelPoints: LoadParcelPoint[]): CandidateRoutePreview {
  if (!option) return { dropMarkers: [], polylines: [] }

  const pointById = new Map(parcelPoints.map((point) => [point.parcel_id, point]))
  const seen = new Set<string>()
  const dropMarkers: OpenStreetMapMarker[] = []
  const polylines: OpenStreetMapPolyline[] = []

  option.loads.forEach((load, loadIndex) => {
    const color = LOAD_COLORS[loadIndex % LOAD_COLORS.length]
    const permittedIds = new Set(load.parcel_ids)
    const previewPoints = load.route_preview ?? []
    const orderedIds = previewPoints
      .filter((point) => point.type === 'parcel' && point.parcel_id && permittedIds.has(point.parcel_id))
      .map((point) => point.parcel_id as string)
    const missingIds = load.parcel_ids.filter((parcelId) => !orderedIds.includes(parcelId))

    for (const parcelId of [...orderedIds, ...missingIds]) {
      if (seen.has(parcelId)) continue
      const source = pointById.get(parcelId)
      const preview = previewPoints.find((point) => point.type === 'parcel' && point.parcel_id === parcelId)
      const latitude = preview?.latitude ?? source?.latitude
      const longitude = preview?.longitude ?? source?.longitude
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) continue
      seen.add(parcelId)
      const sequence = dropMarkers.length + 1
      dropMarkers.push({
        id: parcelId,
        label: String(sequence),
        title: `Stop ${sequence} - ${source?.order_code ?? parcelId}`,
        subtitle: [source?.drop_address, load.load_id].filter(Boolean).join(' - '),
        position: { latitude: latitude as number, longitude: longitude as number },
        color,
      })
    }

    const path = previewPoints
      .filter((point) => point.type === 'branch' || (point.parcel_id && permittedIds.has(point.parcel_id)))
      .map((point) => ({ latitude: point.latitude, longitude: point.longitude }))
    if (path.length > 1) polylines.push({ id: `candidate-route-${load.load_id}`, path, color })
  })

  return { dropMarkers, polylines }
}
