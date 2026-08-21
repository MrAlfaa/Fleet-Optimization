import type { AssignmentValidation, FleetReadiness, VehicleReadiness } from '../types'
import { apiClient } from './apiClient'

type RecordLike = Record<string, unknown>
const stringValue = (value: unknown, fallback = '') => typeof value === 'string' ? value : fallback
const numberValue = (value: unknown) => Number(value ?? 0) || 0
const stringList = (value: unknown) => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []

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

export const intelligenceService = {
  async getFleetReadiness(forecastDate?: string): Promise<FleetReadiness> {
    const raw = await apiClient.get<RecordLike>('/intelligence/fleet-readiness', { query: { forecast_date: forecastDate } })
    return {
      forecastDate: stringValue(raw.forecast_date) || null,
      requiredVehicles: numberValue(raw.required_vehicles),
      eligibleVehicles: numberValue(raw.eligible_vehicles),
      warningVehicles: numberValue(raw.warning_vehicles),
      blockedVehicles: numberValue(raw.blocked_vehicles),
      maintenanceVehicles: numberValue(raw.maintenance_vehicles),
      capacityGap: numberValue(raw.capacity_gap),
      highDemandZones: Array.isArray(raw.high_demand_zones) ? raw.high_demand_zones as RecordLike[] : [],
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
