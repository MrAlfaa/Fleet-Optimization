import { SRI_LANKA_ZONES } from '../data/sriLankaZones'

export interface LocationPoint { latitude: number; longitude: number }

export function haversineKm(a: LocationPoint, b: LocationPoint) {
  const radians = (value: number) => value * Math.PI / 180
  const lat = radians(b.latitude - a.latitude)
  const lng = radians(b.longitude - a.longitude)
  const h = Math.sin(lat / 2) ** 2 + Math.cos(radians(a.latitude)) * Math.cos(radians(b.latitude)) * Math.sin(lng / 2) ** 2
  return 6371 * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h))
}

export function nearestSriLankaZone(point: LocationPoint) {
  return SRI_LANKA_ZONES
    .map((zone) => ({ ...zone, distanceKm: haversineKm(point, zone) }))
    .sort((left, right) => left.distanceKm - right.distanceKm)[0]
}
