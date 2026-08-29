import type { AssignmentValidation, DemandForecastRun, DemandLevel, FleetReadiness, ReadinessDemandZone, VehicleReadiness } from '../types'
import { apiClient } from './apiClient'

type RecordLike = Record<string, unknown>
const stringValue = (value: unknown, fallback = '') => typeof value === 'string' ? value : fallback
const numberValue = (value: unknown) => Number(value ?? 0) || 0
const stringList = (value: unknown) => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
const recordValue = (value: unknown): RecordLike | null => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as RecordLike : null

function mapDemandRun(value: unknown): DemandForecastRun | null {
  const raw = recordValue(value)
  if (!raw) return null
  const planning = recordValue(raw.planning_window)
  return {
    model_run_id: stringValue(raw.model_run_id),
    model_version: stringValue(raw.model_version) || null,
    forecast_start_date: stringValue(raw.forecast_start_date) || null,
    forecast_end_date: stringValue(raw.forecast_end_date) || null,
    horizon_days: numberValue(raw.horizon_days),
    records_generated: numberValue(raw.records_generated),
    zones_count: numberValue(raw.zones_count),
    source_requested: stringValue(raw.source_requested) || null,
    effective_source: stringValue(raw.effective_source) || null,
    fallback_used: raw.fallback_used === true,
    run_type: stringValue(raw.run_type) || null,
    generated_at: stringValue(raw.generated_at) || null,
    activated_at: stringValue(raw.activated_at) || null,
    request_fingerprint: stringValue(raw.request_fingerprint) || null,
    status: stringValue(raw.status) || null,
    planning_window: {
      basis: stringValue(planning?.basis),
      dataset_end_date: stringValue(planning?.dataset_end_date) || null,
      forecast_start_date: stringValue(planning?.forecast_start_date) || null,
      forecast_end_date: stringValue(planning?.forecast_end_date) || null,
      horizon_days: numberValue(planning?.horizon_days),
    },
  }
}

function mapVehicleReadiness(raw: RecordLike): VehicleReadiness {
  const status = stringValue(raw.readiness_status, 'warning')
  return {
    vehicleId: stringValue(raw.vehicle_id),
    registrationNumber: stringValue(raw.registration_number, 'Unknown'),
    vehicleCode: stringValue(raw.vehicle_code, 'Unknown'),
    category: stringValue(raw.vehicle_type, 'other'),
    operationalStatus: stringValue(raw.operational_status, 'unknown'),
    healthStatus: stringValue(raw.health_status, 'unknown'),
    predictionRisk: raw.prediction_risk === null ? null : stringValue(raw.prediction_risk) || null,
    eligible: raw.eligible === true,
    readinessStatus: status === 'ready' || status === 'blocked' ? status : 'warning',
    blockingReasons: stringList(raw.blocking_reasons),
    warnings: stringList(raw.warnings),
  }
}

function mapDemandZone(raw: RecordLike): ReadinessDemandZone {
  const rawLevel = stringValue(raw.demand_level, 'low')
  const demandLevel: DemandLevel = rawLevel === 'very_high' || rawLevel === 'high' || rawLevel === 'medium' ? rawLevel : 'low'
  return {
    operationalZoneId: stringValue(raw.operational_zone_id, stringValue(raw.zone_id)),
    zoneDisplayName: stringValue(raw.zone_display_name, stringValue(raw.operational_zone_id, 'Operational zone')),
    predictedDemand: numberValue(raw.predicted_demand),
    actualDemand: raw.local_actual_demand === null || raw.local_actual_demand === undefined ? null : numberValue(raw.local_actual_demand),
    demandLevel,
    estimatedRequiredVehicles: numberValue(raw.estimated_required_vehicles),
    recommendedAction: stringValue(raw.recommended_action),
  }
}

export const intelligenceService = {
  async getFleetReadiness(forecastDate?: string): Promise<FleetReadiness> {
    const raw = await apiClient.get<RecordLike>('/intelligence/fleet-readiness', { query: { forecast_date: forecastDate } })
    return {
      forecastDate: stringValue(raw.forecast_date) || null,
      activeForecastRun: mapDemandRun(raw.active_run),
      requiredVehicles: numberValue(raw.required_vehicles),
      eligibleVehicles: numberValue(raw.eligible_vehicles),
      warningVehicles: numberValue(raw.warning_vehicles),
      blockedVehicles: numberValue(raw.blocked_vehicles),
      maintenanceVehicles: numberValue(raw.maintenance_vehicles),
      capacityGap: numberValue(raw.capacity_gap),
      highDemandZones: (Array.isArray(raw.high_demand_zones) ? raw.high_demand_zones : []).map((item) => mapDemandZone(item as RecordLike)),
      vehicleReadiness: (Array.isArray(raw.vehicle_readiness) ? raw.vehicle_readiness : []).map((item) => mapVehicleReadiness(item as RecordLike)),
      operationalConflicts: Array.isArray(raw.operational_conflicts) ? raw.operational_conflicts as FleetReadiness['operationalConflicts'] : [],
      recommendations: Array.isArray(raw.recommendations) ? raw.recommendations as FleetReadiness['recommendations'] : [],
      dataContext: stringValue(raw.data_context),
      dataContextNote: stringValue(raw.data_context_note),
    }
  },
  async validateAssignment(vehicleId: string, routeId: string): Promise<AssignmentValidation> {
    const raw = await apiClient.post<RecordLike>('/intelligence/validate-assignment', { vehicle_id: vehicleId, route_id: routeId })
    return {
      eligible: raw.eligible === true,
      readinessStatus: stringValue(raw.readiness_status),
      vehicleRegistration: stringValue(raw.vehicle_registration),
      vehicleCode: stringValue(raw.vehicle_code),
      vehicleType: stringValue(raw.vehicle_type),
      routeCode: stringValue(raw.route_code),
      blockingReasons: stringList(raw.blocking_reasons),
      warnings: stringList(raw.warnings),
      maintenanceRisk: stringValue(raw.maintenance_risk, 'unknown'),
      routeDelayProbability: numberValue(raw.route_delay_probability),
    }
  },
}
