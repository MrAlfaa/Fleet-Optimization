import type {
  Alert,
  DemandForecast,
  DemandZone,
  DeliveryOrder,
  MaintenanceRecord,
  ModelStatus,
  RoutePlan,
  RouteStop,
  RiskLevel,
  User,
  UserRole,
  Vehicle,
  VehiclePart,
} from '../types'
import { localizeZoneText, vehicleCategoryLabel, zoneDisplayName } from '../data/sriLankaZones'

type RecordLike = Record<string, unknown>

const asString = (value: unknown, fallback = '') => (typeof value === 'string' && value.trim() ? value : fallback)
const asNumber = (value: unknown, fallback = 0) => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : fallback
  }
  return fallback
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/+$/, '')

function mediaUrl(value: unknown): string | null {
  const path = asString(value)
  if (!path) return null
  if (/^https?:\/\//i.test(path)) return path
  try {
    const apiUrl = new URL(API_BASE_URL, window.location.origin)
    return new URL(path, apiUrl.origin).toString()
  } catch {
    return null
  }
}

export function formatDate(value: unknown, fallback = 'Not scheduled') {
  if (!value || typeof value !== 'string') return fallback
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return fallback
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export function formatTime(value: unknown, fallback = 'Now') {
  if (!value || typeof value !== 'string') return fallback
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return fallback
  return date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

export function toRiskLevel(value: unknown): RiskLevel {
  return value === 'critical' || value === 'high' || value === 'medium' || value === 'low' ? value : 'medium'
}

export function mapUser(raw: RecordLike): User {
  return {
    id: asString(raw.id),
    name: asString(raw.full_name, asString(raw.name, 'FleetOpt User')),
    email: asString(raw.email),
    role: asString(raw.role, 'fleet_manager') as UserRole,
    organization: asString(raw.organization, 'FleetOpt AI'),
    permissions: Array.isArray(raw.permissions) ? raw.permissions.filter((value): value is string => typeof value === 'string') : [],
  }
}

export function mapVehicle(raw: RecordLike): Vehicle {
  const status = asString(raw.status)
  const health = asString(raw.health_status)
  return {
    id: asString(raw.id),
    number: asString(raw.registration_number, asString(raw.vehicle_code, 'Unknown')),
    registrationNumber: asString(raw.registration_number, asString(raw.vehicle_code, 'Unknown')),
    vehicleCode: asString(raw.vehicle_code, 'Unknown'),
    imageUrl: mediaUrl(raw.image_url),
    category: vehicleCategoryLabel(asString(raw.vehicle_type, 'other')),
    brand: asString(raw.brand, 'EV'),
    modelName: asString(raw.model, 'Vehicle'),
    year: asNumber(raw.year),
    batteryCapacityKwh: asNumber(raw.battery_capacity_kwh),
    model: `${asString(raw.brand, 'EV')} ${asString(raw.model, 'Vehicle')}`.trim(),
    type: asString(raw.vehicle_type, 'EV'),
    assignedDriver: asString(raw.assigned_driver_id, 'Unassigned'),
    mileage: asNumber(raw.current_mileage),
    status:
      status === 'retired'
        ? 'Retired'
        : status === 'under_maintenance'
        ? 'Maintenance'
        : status === 'inactive'
          ? 'Offline'
          : 'Active',
    backendStatus: status,
    risk: health === 'critical' ? 'critical' : health === 'warning' ? 'high' : health === 'healthy' ? 'low' : 'medium',
    lastServiceDate: formatDate(raw.last_service_date, 'No service record'),
    nextServiceDueDate: formatDate(raw.next_service_due_date, 'Not scheduled'),
  }
}

export function mapVehiclePart(raw: RecordLike): VehiclePart {
  return {
    id: asString(raw.id),
    vehicleId: asString(raw.vehicle_id),
    name: asString(raw.part_name, 'Vehicle Part'),
    lastService: formatDate(raw.last_serviced_date, 'No service record'),
    failures: asNumber(raw.failure_count),
    risk: toRiskLevel(raw.risk_level),
    riskScore: asNumber(raw.risk_score),
    status: asString(raw.status, 'unknown'),
    predictedNext: formatDate(raw.next_predicted_maintenance_date, 'No prediction'),
    note: asString(raw.notes, `${asString(raw.status, 'unknown')} status, score ${asNumber(raw.risk_score)}%`),
    category: asString(raw.part_category, 'other'),
    isActive: raw.is_active !== false,
    archivedAt: raw.archived_at ? asString(raw.archived_at) : null,
  }
}

export function mapMaintenanceRecord(raw: RecordLike, vehicles: Vehicle[] = []): MaintenanceRecord {
  const status = asString(raw.status)
  const vehicle = vehicles.find((item) => item.id === raw.vehicle_id)
  const date = raw.service_date
  const isOverdue = typeof date === 'string' && new Date(date).getTime() < Date.now() && status !== 'completed'
  return {
    id: asString(raw.id),
    vehicleId: asString(raw.vehicle_id),
    date: formatDate(date),
    vehicle: vehicle?.number ?? asString(raw.vehicle_id, 'Unknown vehicle'),
    partName: asString(raw.part_name, 'General'),
    maintenanceType: asString(raw.maintenance_type, 'maintenance'),
    priority: asString(raw.priority, 'medium'),
    service: `${asString(raw.part_name, 'General')} - ${asString(raw.maintenance_type, 'maintenance')}`,
    technician: asString(raw.technician_name, 'Unassigned'),
    cost: raw.cost === null || raw.cost === undefined ? '-' : `$${asNumber(raw.cost).toFixed(2)}`,
    costValue: asNumber(raw.cost),
    status: status === 'completed' ? 'Completed' : status === 'cancelled' ? 'Cancelled' : isOverdue ? 'Overdue' : 'Pending Parts',
  }
}

export function mapAlert(raw: RecordLike): Alert {
  const severity = asString(raw.severity)
  const status = asString(raw.status)
  const category = asString(raw.alert_type)
  return {
    id: asString(raw.id),
    time: formatTime(raw.created_at),
    title: localizeZoneText(asString(raw.title, 'Operational alert')),
    description: localizeZoneText(asString(raw.message)),
    severity: severity === 'critical' ? 'critical' : severity === 'high' || severity === 'medium' ? 'warning' : 'info',
    category:
      category === 'route' || category === 'demand' || category === 'driver' || category === 'maintenance'
        ? category
        : 'maintenance',
    vehicle: asString(raw.linked_vehicle_id, 'System'),
    acknowledged: status === 'resolved' || status === 'dismissed',
  }
}

export function mapDemandForecast(raw: RecordLike): DemandForecast {
  const predicted = asNumber(raw.final_predicted_demand, asNumber(raw.predicted_demand, asNumber(raw.graph_enhanced_forecast)))
  const baseline = asNumber(raw.baseline_prophet_forecast)
  const actual = asNumber(raw.local_actual_demand)
  const variance = actual > 0 ? Number((((predicted - actual) / actual) * 100).toFixed(1)) : baseline > 0 ? Number((((predicted - baseline) / baseline) * 100).toFixed(1)) : 0
  return {
    zoneId: asString(raw.operational_zone_id, asString(raw.zone_id)),
    zone: zoneDisplayName(asString(raw.zone_display_name, asString(raw.operational_zone_id, asString(raw.zone_id, 'Unknown zone')))),
    currentVolume: Math.round(actual),
    predictedVolume: Math.round(predicted),
    variance,
    action: asString(raw.recommended_action, predicted >= 50 ? 'Allocate additional vehicle capacity' : 'Normal capacity'),
    rawMappedForecast: asNumber(raw.raw_mapped_forecast, asNumber(raw.predicted_demand)),
    calibrationStatus: asString(raw.calibration_status) === 'active' ? 'active' : 'insufficient_history',
    calibrationFactor: raw.calibration_factor === null || raw.calibration_factor === undefined ? null : asNumber(raw.calibration_factor),
    historyDays: asNumber(raw.history_days),
  }
}

export function mapDemandZone(raw: RecordLike): DemandZone {
  const predicted = asNumber(raw.predicted_demand, asNumber(raw.customer_count))
  const level = asString(raw.demand_level)
  return {
    id: asString(raw.operational_zone_id, asString(raw.id, asString(raw.zone_id))),
    name: zoneDisplayName(asString(raw.zone_display_name, asString(raw.zone_name, asString(raw.operational_zone_id, asString(raw.zone_id, 'Unknown zone'))))),
    predicted,
    actual: asNumber(raw.customer_count),
    overloadScore: predicted,
    risk: level === 'very_high' ? 'critical' : level === 'high' ? 'high' : level === 'medium' ? 'medium' : 'low',
  }
}

export function mapDeliveryOrder(raw: RecordLike): DeliveryOrder {
  const priority = asString(raw.priority)
  const status = asString(raw.delivery_status)
  return {
    id: asString(raw.id),
    orderCode: asString(raw.order_code, asString(raw.id)),
    customer: asString(raw.customer_name, asString(raw.order_code, 'Delivery order')),
    priority: priority === 'urgent' ? 'Critical' : priority === 'high' ? 'High' : 'Standard',
    timeWindow: formatDate(raw.scheduled_date, 'Anytime'),
    zone: zoneDisplayName(asString(raw.zone_display_name, asString(raw.operational_zone_id, asString(raw.zone_id, 'Unassigned zone')))),
    location: asString(raw.drop_address, `${asNumber(raw.drop_latitude).toFixed(4)}, ${asNumber(raw.drop_longitude).toFixed(4)}`),
    status: status === 'in_route' ? 'In Transit' : status === 'assigned' || status === 'delivered' ? 'Routed' : 'Unassigned',
    backendStatus: status,
    pickupLatitude: asNumber(raw.pickup_latitude),
    pickupLongitude: asNumber(raw.pickup_longitude),
    dropLatitude: asNumber(raw.drop_latitude),
    dropLongitude: asNumber(raw.drop_longitude),
    pickupAddress: asString(raw.pickup_address),
    dropAddress: asString(raw.drop_address),
    zoneId: asString(raw.operational_zone_id, asString(raw.zone_id)),
    scheduledDate: asString(raw.scheduled_date),
    assignedVehicleId: raw.assigned_vehicle_id ? asString(raw.assigned_vehicle_id) : null,
    assignedDriverId: raw.assigned_driver_id ? asString(raw.assigned_driver_id) : null,
  }
}

export function mapRoutePlan(raw: RecordLike): RoutePlan {
  const stops = Array.isArray(raw.optimized_stop_order) ? raw.optimized_stop_order : []
  const mappedStops: RouteStop[] = stops.map((stop, index) => {
    const item = stop as RecordLike
    const latitude = item.latitude === undefined || item.latitude === null ? null : asNumber(item.latitude)
    const longitude = item.longitude === undefined || item.longitude === null ? null : asNumber(item.longitude)
    return {
      sequence: index + 1,
      name: asString(item.order_code, asString(item.label, index === 0 ? 'Depot' : `Stop ${index}`)),
      eta: item.predicted_eta_minutes ? `${Math.round(asNumber(item.predicted_eta_minutes))} min` : '--',
      loadDrop: item.parcel_weight ? `${asNumber(item.parcel_weight)} kg` : '--',
      status: index === 0 ? 'Origin' : 'Pending',
      latitude,
      longitude,
    }
  })
  const segmentRows = Array.isArray(raw.segments) ? raw.segments : []
  const segmentPath = segmentRows.flatMap((segment, index) => {
    const item = segment as RecordLike
    const from = {
      latitude: asNumber(item.from_latitude),
      longitude: asNumber(item.from_longitude),
    }
    const to = {
      latitude: asNumber(item.to_latitude),
      longitude: asNumber(item.to_longitude),
    }
    return index === 0 ? [from, to] : [to]
  }).filter((point) => Number.isFinite(point.latitude) && Number.isFinite(point.longitude))
  const stopPath = mappedStops
    .filter((stop) => stop.latitude !== null && stop.longitude !== null)
    .map((stop) => ({ latitude: stop.latitude as number, longitude: stop.longitude as number }))

  return {
    id: asString(raw.id),
    vehicle: asString(raw.vehicle_id, 'Unassigned'),
    driver: asString(raw.driver_id, 'Unassigned'),
    distance: `${Math.round(asNumber(raw.total_route_cost_score))} cost`,
    eta: `${Math.round(asNumber(raw.total_predicted_eta_minutes))} min`,
    capacityUse: Math.min(100, mappedStops.length * 12),
    stops: mappedStops,
    mapPath: segmentPath.length > 1 ? segmentPath : stopPath,
    warning: asString((raw.maintenance_context as RecordLike | undefined)?.warning, asString((raw.demand_context as RecordLike | undefined)?.warning, 'No critical route warning returned.')),
    weatherAvailable: (raw.weather_context as RecordLike | undefined)?.available === true,
    weatherWarnings: Array.isArray((raw.weather_context as RecordLike | undefined)?.warnings) ? ((raw.weather_context as RecordLike).warnings as unknown[]).map(String) : [],
  }
}

export function modelStatusFromAvailability(raw: RecordLike): ModelStatus {
  if (raw.available === true && raw.loaded === true) return 'Loaded'
  if (raw.available === true) return 'Available'
  if (raw.artifact_exists === false || raw.model_bundle_exists === false || raw.model_file_exists === false) return 'Artifact missing'
  return 'Unavailable'
}
