import type { MapPoint, OpenStreetMapMarker } from '../components/OpenStreetMapPanel'
import type { LiveTrip, LiveTripLocation } from '../types'

export interface LiveMapView {
  markers: OpenStreetMapMarker[]
  trail: MapPoint[]
  selectedTrip: LiveTrip | null
  progress: {
    completedStops: number
    totalStops: number
  }
}

function isValidCoordinate(latitude: number, longitude: number) {
  return Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    Math.abs(latitude) <= 90 &&
    Math.abs(longitude) <= 180
}

export function buildLiveMapView(trips: LiveTrip[], locations: LiveTripLocation[]): LiveMapView {
  const selectedTrip = trips.find((trip) => trip.tripStatus === 'active') ?? trips[0] ?? null
  const progress = trips.reduce(
    (total, trip) => ({
      completedStops: total.completedStops + trip.progress.completedStops,
      totalStops: total.totalStops + trip.progress.totalStops,
    }),
    { completedStops: 0, totalStops: 0 },
  )

  const markers = trips.flatMap((trip, index) => {
    const location = trip.latestLocation
    if (!location || !isValidCoordinate(location.latitude, location.longitude)) return []

    return [{
      id: trip.routeId,
      label: String(index + 1),
      title: `${trip.routeCode} - ${trip.driverName}`,
      subtitle: `${trip.vehicleCode} | ${trip.progress.completedStops}/${trip.progress.totalStops} stops | ${location.recordedAt}`,
      position: {
        latitude: location.latitude,
        longitude: location.longitude,
      },
      color: trip.tripStatus === 'active' ? '#16A34A' : '#1D4ED8',
    }]
  })

  const trail = locations
    .filter((location) => isValidCoordinate(location.latitude, location.longitude))
    .toSorted((left, right) => Date.parse(left.recordedAt) - Date.parse(right.recordedAt))
    .map((location) => ({ latitude: location.latitude, longitude: location.longitude }))

  return { markers, trail, selectedTrip, progress }
}
