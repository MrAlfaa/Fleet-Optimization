import type {
  Alert,
  DemandForecast,
  DemandZone,
  DeliveryOrder,
  MaintenanceRecord,
  MaintenancePrediction,
  MaintenanceReview,
  InspectionAssignee,
  ModelStatus,
  RoutePlan,
  RouteStop,
  RiskLevel,
  User,
  UserRole,
  Vehicle,
  VehiclePart,
  VehicleMaintenanceInspection,
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
  const latestAssessmentRisk = asString(raw.latest_assessment_risk)
  const loadProfile = raw.load_profile && typeof raw.load_profile === 'object' ? raw.load_profile as RecordLike : null
  return {
    id: asString(raw.id),
    number: asString(raw.registration_number, asString(raw.vehicle_code, 'Unknown')),
    registrationNumber: asString(raw.registration_number, asString(raw.vehicle_code, 'Unknown')),
    vehicleCode: asString(raw.vehicle_code, 'Unknown'),
    imageUrl: mediaUrl(raw.image_url),
    category: raw.vehicle_category ? titleCase(asString(raw.vehicle_category)) : vehicleCategoryLabel(asString(raw.vehicle_type, 'other')),
    vehicleCategory: canonicalVehicleCategory(raw.vehicle_category, raw.vehicle_type),
    fuelType: canonicalFuelType(raw.fuel_type, raw.vehicle_type),
    inServiceDate: isoDateInput(raw.in_service_date),
    payloadCapacityKg: asNumber(raw.payload_capacity_kg),
    loadProfile: loadProfile ? {
      profileCode: asString(loadProfile.profile_code), capacityM3: asNumber(loadProfile.capacity_m3),
      cargoLengthCm: asNumber(loadProfile.cargo_length_cm), cargoWidthCm: asNumber(loadProfile.cargo_width_cm), cargoHeightCm: asNumber(loadProfile.cargo_height_cm),
      maxParcels: asNumber(loadProfile.max_parcels), maxStackLayers: asNumber(loadProfile.max_stack_layers),
      vehicleMaxStackWeightKg: asNumber(loadProfile.vehicle_max_stack_weight_kg), isRefrigerated: loadProfile.is_refrigerated === true,
      tempMinCelsius: optionalNumber(loadProfile.temp_min_celsius) ?? null, tempMaxCelsius: optionalNumber(loadProfile.temp_max_celsius) ?? null,
      isHazmatCertified: loadProfile.is_hazmat_certified === true, hasTailLift: loadProfile.has_tail_lift === true,
      availableFrom: asString(loadProfile.available_from, '00:00'), availableUntil: asString(loadProfile.available_until, '23:59'),
    } : null,
    brand: asString(raw.brand, 'EV'),
    modelName: asString(raw.model, 'Vehicle'),
    year: asNumber(raw.year),
    batteryCapacityKwh: asNumber(raw.battery_capacity_kwh),
    model: `${asString(raw.brand, 'EV')} ${asString(raw.model, 'Vehicle')}`.trim(),
    type: asString(raw.vehicle_type, 'EV'),
    assignedDriver: asString(
      raw.assigned_driver_name,
      asString(raw.assigned_driver_username, 'Unassigned'),
    ),
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
    risk: latestAssessmentRisk
      ? toRiskLevel(latestAssessmentRisk)
      : health === 'critical' ? 'critical' : health === 'warning' ? 'high' : health === 'healthy' ? 'low' : 'medium',
    lastServiceDate: formatDate(raw.last_service_date, 'No service record'),
    nextServiceDueDate: formatDate(raw.next_service_due_date, 'Not scheduled'),
    onboardingType: raw.onboarding_type === 'brand_new' ? 'brand_new' : 'existing_fleet',
    commissioningStatus: raw.commissioning_status === 'pending' || raw.commissioning_status === 'passed' || raw.commissioning_status === 'failed' ? raw.commissioning_status : 'not_started',
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
    maintenanceSystem: asString(raw.maintenance_system, asString(raw.part_category, 'general')),
    eventKind: canonicalEventKind(raw.event_kind),
    priority: asString(raw.priority, 'medium'),
    service: `${asString(raw.part_name, 'General')} - ${asString(raw.maintenance_type, 'maintenance')}`,
    technician: asString(raw.technician_name, 'Unassigned'),
    cost: raw.cost === null || raw.cost === undefined ? '-' : `LKR ${asNumber(raw.cost).toFixed(2)}`,
    costValue: asNumber(raw.cost),
    status: status === 'completed' ? 'Completed' : status === 'cancelled' ? 'Cancelled' : isOverdue ? 'Overdue' : 'Pending Parts',
    serviceDate: asString(raw.service_date),
    issueType: asString(raw.issue_type, asString(raw.maintenance_type, 'Service work')),
    workOrderStatus: canonicalWorkOrderStatus(raw.work_order_status),
    inspectionId: optionalString(raw.inspection_id),
    assessmentId: optionalString(raw.assessment_id),
    estimatedCost: optionalNumber(raw.estimated_cost) ?? null,
    actualCost: optionalNumber(raw.actual_cost) ?? null,
    startedAt: optionalString(raw.started_at),
    completedAt: optionalString(raw.completed_at),
    completionEvidence: optionalString(raw.completion_evidence),
    cancellationReason: optionalString(raw.cancellation_reason),
    createdAt: asString(raw.created_at),
    updatedAt: asString(raw.updated_at),
    notes: asString(raw.notes),
    serviceCenter: asString(raw.service_center),
  }
}

export function mapMaintenancePrediction(raw: RecordLike): MaintenancePrediction {
  const legacyName = asString(raw.maintenance_type_name, asString(raw.part_name))
  const rows = Array.isArray(raw.system_risks) ? raw.system_risks : legacyName ? [{ system: legacyName, probability: raw.failure_probability, risk_level: raw.risk_level }] : []
  const legacyRul = asNumber(raw.predicted_rul, -1)
  const legacyUnit = asString(raw.rul_unit)
  const planningRaw = raw.planning_window && typeof raw.planning_window === 'object' ? raw.planning_window as RecordLike : null
  const planningDays = planningRaw?.days && typeof planningRaw.days === 'object' ? planningRaw.days as RecordLike : null
  const planningKm = planningRaw?.km && typeof planningRaw.km === 'object' ? planningRaw.km as RecordLike : null
  const planningWindow = planningRaw ? {
    minimumDays: optionalNumber(planningDays?.lower ?? planningRaw.minimum_days ?? planningRaw.min_days),
    maximumDays: optionalNumber(planningDays?.upper ?? planningRaw.maximum_days ?? planningRaw.max_days),
    minimumKm: optionalNumber(planningKm?.lower ?? planningRaw.minimum_km ?? planningRaw.min_km),
    maximumKm: optionalNumber(planningKm?.upper ?? planningRaw.maximum_km ?? planningRaw.max_km),
  } : legacyRul >= 0 ? {
    maximumDays: legacyUnit.toLowerCase().startsWith('day') ? legacyRul : undefined,
    maximumKm: legacyUnit.toLowerCase().includes('km') ? legacyRul : undefined,
  } : null
  const reviewStatus = asString(raw.review_status, 'not_required')
  return {
    id: asString(raw.id, asString(raw.prediction_id)),
    vehicleId: asString(raw.vehicle_id),
    vehicleRegistration: asString(raw.vehicle_registration, asString(raw.registration_number, asString(raw.vehicle_id, 'Unknown vehicle'))),
    vehicleCode: asString(raw.vehicle_code),
    risk: toRiskLevel(raw.risk_level),
    probability30Days: asNumber(raw.failure_probability_30_days, asNumber(raw.failure_probability)),
    probability2000Km: asNumber(raw.failure_probability_2000_km),
    systemRisks: rows.map((value) => {
      const item = value as RecordLike
      const key = asString(item.system, asString(item.maintenance_system, asString(item.name, 'general')))
      return { key, name: titleCase(key), probability: asNumber(item.probability, asNumber(item.risk_probability, asNumber(raw.failure_probability))), risk: toRiskLevel(item.risk_level ?? raw.risk_level) }
    }),
    planningStatus: asString(raw.planning_status, planningWindow ? 'planning_window_available' : 'no_near_term_failure_indicated'),
    planningWindow,
    dataQuality: asString(raw.data_quality, asString((raw.feature_snapshot as RecordLike | undefined)?.quality_grade, 'unknown')),
    defaultedFields: stringArray(raw.defaulted_fields ?? (raw.feature_snapshot as RecordLike | undefined)?.defaulted_fields),
    reviewStatus: reviewStatus === 'pending' || reviewStatus === 'cleared' || reviewStatus === 'confirmed' ? reviewStatus : 'not_required',
    dispatchHold: raw.dispatch_hold === true,
    modelVersion: asString(raw.model_version),
    featureSchemaVersion: asString(raw.feature_snapshot_version, asString(raw.feature_schema_version)),
    createdAt: asString(raw.created_at, asString(raw.prediction_date)),
    featureHash: asString(raw.feature_hash),
    reviewId: asString(raw.prediction_review_id, asString(raw.review_id, asString((raw.review as RecordLike | undefined)?.id))),
  }
}

export function mapPredictionReview(raw: RecordLike): MaintenanceReview {
  const status = asString(raw.status, 'pending')
  return {
    id: asString(raw.id), vehicleId: asString(raw.vehicle_id),
    vehicleRegistration: asString(raw.vehicle_registration, asString(raw.registration_number, asString(raw.vehicle_id, 'Unknown vehicle'))),
    vehicleCode: asString(raw.vehicle_code), predictionId: asString(raw.prediction_id), featureHash: asString(raw.feature_hash),
    risk: toRiskLevel(raw.risk_level), status: status === 'cleared' || status === 'confirmed' ? status : 'pending',
    notes: asString(raw.notes), createdAt: asString(raw.created_at), updatedAt: asString(raw.updated_at, asString(raw.created_at)),
    resolvedAt: raw.resolved_at ? asString(raw.resolved_at) : null, resolvedBy: asString(raw.resolved_by),
  }
}

export function mapInspection(raw: RecordLike): VehicleMaintenanceInspection {
  const checklist = Array.isArray(raw.checklist) ? raw.checklist : []
  const draftChecklist = Array.isArray(raw.draft_checklist) ? raw.draft_checklist : []
  const status = asString(raw.status, 'pending') as VehicleMaintenanceInspection['status']
  const priority = asString(raw.priority, 'medium') as VehicleMaintenanceInspection['priority']
  return {
    id: asString(raw.id),
    vehicleId: asString(raw.vehicle_id),
    inspectionType: raw.inspection_type === 'commissioning' ? 'commissioning' : 'risk_assessment',
    assessmentId: raw.assessment_id ? asString(raw.assessment_id) : null,
    featureHash: asString(raw.feature_hash),
    status,
    isActive: raw.is_active !== false,
    priority,
    inspectionAreas: stringArray(raw.inspection_areas),
    notes: raw.notes ? asString(raw.notes) : null,
    checklist: checklist.map((value) => {
      const item = value as RecordLike
      return {
        key: asString(item.key),
        label: asString(item.label),
        outcome: asString(item.outcome, 'not_applicable') as VehicleMaintenanceInspection['checklist'][number]['outcome'],
        remark: item.remark ? asString(item.remark) : null,
      }
    }),
    summary: raw.summary ? asString(raw.summary) : null,
    draftChecklist: draftChecklist.map(mapInspectionChecklistItem),
    draftSummary: raw.draft_summary ? asString(raw.draft_summary) : null,
    draftSavedBy: raw.draft_saved_by ? asString(raw.draft_saved_by) : null,
    draftSavedAt: raw.draft_saved_at ? asString(raw.draft_saved_at) : null,
    assignedTo: raw.assigned_to ? asString(raw.assigned_to) : null,
    assignedBy: raw.assigned_by ? asString(raw.assigned_by) : null,
    assignedAt: raw.assigned_at ? asString(raw.assigned_at) : null,
    startedBy: raw.started_by ? asString(raw.started_by) : null,
    startedAt: raw.started_at ? asString(raw.started_at) : null,
    completedBy: raw.completed_by ? asString(raw.completed_by) : null,
    completedAt: raw.completed_at ? asString(raw.completed_at) : null,
    decision: raw.decision === 'maintenance_required' || raw.decision === 'returned_to_service' ? raw.decision : null,
    decisionNotes: raw.decision_notes ? asString(raw.decision_notes) : null,
    decidedBy: raw.decided_by ? asString(raw.decided_by) : null,
    decidedAt: raw.decided_at ? asString(raw.decided_at) : null,
    workOrderId: raw.work_order_id ? asString(raw.work_order_id) : null,
    cancellationReason: raw.cancellation_reason ? asString(raw.cancellation_reason) : null,
    createdBy: asString(raw.created_by),
    createdAt: asString(raw.created_at),
    updatedAt: asString(raw.updated_at, asString(raw.created_at)),
  }
}

function mapInspectionChecklistItem(value: unknown): VehicleMaintenanceInspection['checklist'][number] {
  const item = value as RecordLike
  return {
    key: asString(item.key),
    label: asString(item.label),
    outcome: asString(item.outcome, 'not_applicable') as VehicleMaintenanceInspection['checklist'][number]['outcome'],
    remark: item.remark ? asString(item.remark) : null,
  }
}

export function mapInspectionAssignee(raw: RecordLike): InspectionAssignee {
  return {
    id: asString(raw.id),
    fullName: asString(raw.full_name, 'Maintenance team member'),
    role: raw.role === 'admin' ? 'admin' : 'maintenance_manager',
  }
}

function optionalNumber(value: unknown): number | undefined {
  if (value === null || value === undefined || value === '') return undefined
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : undefined
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function titleCase(value: string) {
  return value.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase())
}

function isoDateInput(value: unknown) {
  const raw = asString(value)
  return raw ? raw.slice(0, 10) : undefined
}

function canonicalVehicleCategory(value: unknown, legacy: unknown): Vehicle['vehicleCategory'] {
  const normalized = asString(value, asString(legacy)).toLowerCase()
  if (normalized.includes('truck')) return 'truck'
  if (normalized.includes('bus')) return 'bus'
  if (normalized.includes('car')) return 'car'
  return 'van'
}

function canonicalFuelType(value: unknown, legacy: unknown): Vehicle['fuelType'] {
  const normalized = asString(value, asString(legacy)).toLowerCase()
  if (normalized.includes('hybrid')) return 'hybrid'
  if (normalized.includes('diesel')) return 'diesel'
  if (normalized.includes('petrol')) return 'petrol'
  return 'electric'
}

function canonicalEventKind(value: unknown): MaintenanceRecord['eventKind'] {
  const normalized = asString(value, 'inspection')
  return normalized === 'scheduled_service' || normalized === 'corrective_repair' || normalized === 'breakdown' ? normalized : 'inspection'
}

function canonicalWorkOrderStatus(value: unknown): MaintenanceRecord['workOrderStatus'] {
  return value === 'planned' || value === 'approved' || value === 'in_progress' || value === 'completed' || value === 'cancelled' ? value : null
}

function optionalString(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null
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
  const baseline = optionalNumber(raw.baseline_forecast ?? raw.baseline_prophet_forecast)
  const actualAvailable = raw.local_actual_demand !== null && raw.local_actual_demand !== undefined
  const actual = asNumber(raw.local_actual_demand)
  const calculatedVariance = actualAvailable && actual > 0 ? Number((((predicted - actual) / actual) * 100).toFixed(1)) : 0
  const variance = raw.variance_percentage === null || raw.variance_percentage === undefined
    ? calculatedVariance
    : asNumber(raw.variance_percentage)
  const rawLevel = asString(raw.demand_level, 'low')
  const demandLevel = rawLevel === 'very_high' || rawLevel === 'high' || rawLevel === 'medium' ? rawLevel : 'low'
  const date = asString(raw.date, asString(raw.forecast_date)).slice(0, 10)
  return {
    zoneId: asString(raw.operational_zone_id, asString(raw.zone_id)),
    zone: zoneDisplayName(asString(raw.zone_display_name, asString(raw.operational_zone_id, asString(raw.zone_id, 'Unknown zone')))),
    date,
    currentVolume: Math.round(actual),
    actualAvailable,
    predictedVolume: Math.round(predicted),
    variance,
    varianceOrders: raw.variance_orders === null || raw.variance_orders === undefined ? null : asNumber(raw.variance_orders),
    action: asString(raw.recommended_action, demandLevel === 'very_high' || demandLevel === 'high' ? 'Reserve additional vehicle capacity' : 'Maintain planned capacity'),
    demandLevel,
    requiredVehicles: asNumber(raw.estimated_required_vehicles),
    baselineForecast: baseline ?? null,
    lowerBound: optionalNumber(raw.lower_bound ?? raw.yhat_lower) ?? null,
    upperBound: optionalNumber(raw.upper_bound ?? raw.yhat_upper) ?? null,
    modelVersion: asString(raw.model_version),
    generatedAt: asString(raw.generated_at),
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
  const loadProfile = raw.load_profile && typeof raw.load_profile === 'object' ? raw.load_profile as RecordLike : null
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
    deliveryDate: asString(raw.delivery_date, asString(raw.scheduled_date).slice(0, 10)),
    deliveryPeriod: raw.delivery_period === 'second_half' ? 'second_half' : 'first_half',
    pickupSource: asString(raw.pickup_source),
    customerPhone: asString(raw.customer_phone),
    parcelWeight: optionalNumber(raw.parcel_weight) ?? null,
    parcelVolume: optionalNumber(raw.parcel_volume) ?? null,
    loadProfile: loadProfile ? {
      lengthCm: asNumber(loadProfile.length_cm), widthCm: asNumber(loadProfile.width_cm), heightCm: asNumber(loadProfile.height_cm), volumeM3: asNumber(loadProfile.volume_m3),
      fragile: loadProfile.fragile === true, stackable: loadProfile.stackable !== false, maxStackWeightKg: asNumber(loadProfile.max_stack_weight_kg),
      loadingOrientationFixed: loadProfile.loading_orientation_fixed === true, hazardous: loadProfile.hazardous === true,
      hazmatClass: optionalString(loadProfile.hazmat_class), requiresRefrigeration: loadProfile.requires_refrigeration === true,
      tempMinCelsius: optionalNumber(loadProfile.temp_min_celsius) ?? null, tempMaxCelsius: optionalNumber(loadProfile.temp_max_celsius) ?? null,
      twoPersonLift: loadProfile.two_person_lift === true, doNotTilt: loadProfile.do_not_tilt === true,
      serviceType: asString(loadProfile.service_type, 'door_to_door'), optimizationEligible: loadProfile.optimization_eligible === true,
      eligibilityReasons: stringArray(loadProfile.eligibility_reasons), dataQualityFlags: stringArray(loadProfile.data_quality_flags),
    } : null,
    loadPlanningStatus: asString(raw.load_planning_status, 'unplanned'),
    activeConsolidationId: optionalString(raw.active_consolidation_id),
    activeLoadPlanId: optionalString(raw.active_load_plan_id),
    assignedVehicleId: raw.assigned_vehicle_id ? asString(raw.assigned_vehicle_id) : null,
    assignedDriverId: raw.assigned_driver_id ? asString(raw.assigned_driver_id) : null,
  }
}

export function mapRoutePlan(raw: RecordLike): RoutePlan {
  const stops = Array.isArray(raw.optimized_stop_order) ? raw.optimized_stop_order : []
  let deliverySequence = 0
  const mappedStops: RouteStop[] = stops.map((stop, index) => {
    const item = stop as RecordLike
    const isBranch = item.type === 'depot'
    if (!isBranch) deliverySequence += 1
    const latitude = item.latitude === undefined || item.latitude === null ? null : asNumber(item.latitude)
    const longitude = item.longitude === undefined || item.longitude === null ? null : asNumber(item.longitude)
    return {
      sequence: isBranch ? (index === 0 ? 0 : deliverySequence + 1) : deliverySequence,
      name: isBranch ? (index === 0 ? 'Colombo Central Branch' : 'Return to Colombo Central Branch') : asString(item.order_code, asString(item.label, `Stop ${index}`)),
      eta: item.predicted_eta_minutes ? `${Math.round(asNumber(item.predicted_eta_minutes))} min` : '--',
      loadDrop: item.parcel_weight ? `${asNumber(item.parcel_weight)} kg` : '--',
      status: isBranch ? (index === 0 ? 'Origin' : 'Return') : 'Pending',
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
    routeCode: asString(raw.route_code),
    status: asString(raw.status, 'optimized') as RoutePlan['status'],
    routeSetId: asString(raw.route_set_id),
    loadPlanId: asString(raw.load_plan_id),
    loadId: asString(raw.load_id),
    consolidationId: asString(raw.consolidation_id),
    vehicle: asString(raw.vehicle_id, 'Unassigned'),
    driver: asString(raw.driver_id, 'Unassigned'),
    distance: `${Math.round(asNumber(raw.total_route_cost_score))} cost`,
    eta: `${Math.round(asNumber(raw.total_predicted_eta_minutes))} min`,
    capacityUse: Math.min(100, mappedStops.length * 12),
    stops: mappedStops,
    deliveryDate: asString(raw.delivery_date),
    deliveryPeriod: raw.delivery_period === 'second_half' ? 'second_half' : raw.delivery_period === 'first_half' ? 'first_half' : undefined,
    mapPath: segmentPath.length > 1 ? segmentPath : stopPath,
    warning: asString((raw.maintenance_context as RecordLike | undefined)?.warning, asString((raw.demand_context as RecordLike | undefined)?.warning, 'No critical route warning returned.')),
    weatherAvailable: (raw.weather_context as RecordLike | undefined)?.available === true,
    weatherWarnings: Array.isArray((raw.weather_context as RecordLike | undefined)?.warnings) ? ((raw.weather_context as RecordLike).warnings as unknown[]).map(String) : [],
    averageDelayProbability: asNumber(raw.average_delay_probability),
  }
}

export function modelStatusFromAvailability(raw: RecordLike): ModelStatus {
  if (raw.available === true && raw.loaded === true) return 'Loaded'
  if (raw.available === true) return 'Available'
  if (raw.artifact_exists === false || raw.model_bundle_exists === false || raw.model_file_exists === false) return 'Artifact missing'
  return 'Unavailable'
}
