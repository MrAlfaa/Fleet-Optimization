import type { Alert, AssessmentEligibility, EvPartCatalogItem, InspectionAssignee, InspectionChecklistItem, InspectionPriority, InspectionStatus, MaintenancePrediction, MaintenanceRecord, MaintenanceReview, MaintenanceSystem, PaginatedResponse, PredictiveModelStatus, Vehicle, VehicleMaintenanceInspection, VehiclePart } from '../types'
import { apiClient } from './apiClient'
import { mapAlert, mapInspection, mapInspectionAssignee, mapMaintenancePrediction, mapMaintenanceRecord, mapPredictionReview, mapVehicle, mapVehiclePart } from './adapters'

type BackendList<T> = PaginatedResponse<T>
type RecordLike = Record<string, unknown>

export interface VehicleCreatePayload {
  vehicle_code: string
  registration_number: string
  vehicle_type: string
  vehicle_category?: string
  brand: string
  model: string
  year: number
  fuel_type?: string
  in_service_date?: string
  payload_capacity_kg?: number
  current_mileage?: number
  battery_capacity_kwh?: number
  onboarding_type?: 'brand_new' | 'existing_fleet'
  load_profile?: {
    profile_code: string
    capacity_m3: number
    cargo_length_cm: number
    cargo_width_cm: number
    cargo_height_cm: number
    max_parcels: number
    max_stack_layers: number
    vehicle_max_stack_weight_kg: number
    is_refrigerated: boolean
    temp_min_celsius?: number
    temp_max_celsius?: number
    is_hazmat_certified: boolean
    has_tail_lift: boolean
    available_from: string
    available_until: string
  }
}

export type VehicleUpdatePayload = Partial<VehicleCreatePayload> & { status?: string }

export interface VehiclePartPayload {
  part_name: string
  part_category: string
  status?: string
  notes?: string
}

export interface MaintenanceCreatePayload {
  vehicle_id: string
  part_id?: string
  part_name: string
  maintenance_type: string
  maintenance_system?: string
  event_kind?: string
  prediction_review_id?: string
  issue_type: string
  service_date: string
  mileage_at_service: number
  technician_name?: string
  service_center?: string
  cost?: number
  status?: string
  priority?: string
  notes?: string
}

export interface InspectionCreatePayload {
  vehicle_id: string
  inspection_type?: 'risk_assessment' | 'commissioning'
  assessment_id?: string
  feature_hash?: string
  priority: InspectionPriority
  inspection_areas: string[]
  notes?: string
}

export interface InspectionDecisionPayload {
  decision: 'returned_to_service' | 'maintenance_required'
  notes: string
  maintenance_system?: MaintenanceSystem
  issue_type?: string
  priority?: InspectionPriority
  estimated_cost?: number
}

export interface MaintenanceListParams {
  vehicle_id?: string
  status?: string
  priority?: string
  maintenance_type?: string
  search?: string
  page?: number
  limit?: number
}

export interface MaintenanceCompletePayload {
  actual_cost: number
  completion_evidence: string
  notes?: string
  technician_name?: string
  service_center?: string
}

export const fleetService = {
  async listInspections(params: { status?: InspectionStatus; vehicle_id?: string; assigned_to?: string; page?: number; limit?: number } = {}): Promise<PaginatedResponse<VehicleMaintenanceInspection>> {
    const data = await apiClient.get<BackendList<RecordLike>>('/inspections', { query: { page: 1, limit: 100, ...params } })
    return { ...data, items: data.items.map(mapInspection) }
  },
  async listInspectionAssignees(): Promise<InspectionAssignee[]> {
    const data = await apiClient.get<{ items: RecordLike[] }>('/inspections/assignees')
    return data.items.map(mapInspectionAssignee)
  },
  async createInspection(payload: InspectionCreatePayload): Promise<VehicleMaintenanceInspection> {
    return mapInspection(await apiClient.post<RecordLike>('/inspections', payload))
  },
  async getInspection(inspectionId: string): Promise<VehicleMaintenanceInspection> {
    return mapInspection(await apiClient.get<RecordLike>(`/inspections/${inspectionId}`))
  },
  async startInspection(inspectionId: string, payload: { notes?: string } = {}): Promise<VehicleMaintenanceInspection> {
    return mapInspection(await apiClient.post<RecordLike>(`/inspections/${inspectionId}/start`, payload))
  },
  async saveInspectionDraft(inspectionId: string, payload: { checklist?: InspectionChecklistItem[]; summary?: string | null }): Promise<VehicleMaintenanceInspection> {
    return mapInspection(await apiClient.patch<RecordLike>(`/inspections/${inspectionId}/draft`, payload))
  },
  async completeInspection(inspectionId: string, payload: { checklist: InspectionChecklistItem[]; summary: string }): Promise<VehicleMaintenanceInspection> {
    return mapInspection(await apiClient.post<RecordLike>(`/inspections/${inspectionId}/complete`, payload))
  },
  async decideInspection(inspectionId: string, payload: InspectionDecisionPayload): Promise<VehicleMaintenanceInspection> {
    return mapInspection(await apiClient.post<RecordLike>(`/inspections/${inspectionId}/decision`, payload))
  },
  async assignInspection(inspectionId: string, payload: { assigned_to: string; notes?: string }): Promise<VehicleMaintenanceInspection> {
    return mapInspection(await apiClient.post<RecordLike>(`/inspections/${inspectionId}/assign`, payload))
  },
  async cancelInspection(inspectionId: string, reason: string): Promise<VehicleMaintenanceInspection> {
    return mapInspection(await apiClient.post<RecordLike>(`/inspections/${inspectionId}/cancel`, { reason }))
  },
  async getEvPartCatalog(): Promise<EvPartCatalogItem[]> {
    const data = await apiClient.get<Array<RecordLike>>('/vehicles/parts/catalog')
    return data.map((item) => ({
      key: String(item.key),
      name: String(item.name),
      category: String(item.category),
      description: String(item.description),
      mlSupported: Boolean(item.ml_supported),
      mlSignalGroup: item.ml_signal_group ? String(item.ml_signal_group) : null,
    }))
  },
  async listVehicles(params: { page?: number; limit?: number; health_status?: string; search?: string } = {}): Promise<Vehicle[]> {
    const data = await apiClient.get<BackendList<RecordLike>>('/vehicles', {
      query: { page: 1, limit: 100, ...params },
    })
    return data.items.map(mapVehicle)
  },
  async createVehicle(payload: VehicleCreatePayload): Promise<Vehicle> {
    const data = await apiClient.post<RecordLike>('/vehicles', {
      fuel_type: 'electric',
      status: 'inactive',
      health_status: 'unknown',
      current_mileage: 0,
      ...payload,
    })
    return mapVehicle(data)
  },
  async updateVehicle(vehicleId: string, payload: VehicleUpdatePayload): Promise<Vehicle> {
    return mapVehicle(await apiClient.put<RecordLike>(`/vehicles/${vehicleId}`, payload))
  },
  async retireVehicle(vehicleId: string, reason?: string): Promise<Vehicle> {
    return mapVehicle(await apiClient.post<RecordLike>(`/vehicles/${vehicleId}/retire`, { reason }))
  },
  async restoreVehicle(vehicleId: string): Promise<Vehicle> {
    return mapVehicle(await apiClient.post<RecordLike>(`/vehicles/${vehicleId}/restore`, {}))
  },
  async uploadVehicleImage(vehicleId: string, image: File): Promise<Vehicle> {
    const formData = new FormData()
    formData.append('image', image)
    return mapVehicle(await apiClient.upload<RecordLike>(`/vehicles/${vehicleId}/image`, formData))
  },
  async deleteVehicleImage(vehicleId: string): Promise<Vehicle> {
    return mapVehicle(await apiClient.delete<RecordLike>(`/vehicles/${vehicleId}/image`))
  },
  async getVehicle(vehicleId: string): Promise<Vehicle> {
    return mapVehicle(await apiClient.get<RecordLike>(`/vehicles/${vehicleId}`))
  },
  async listVehicleParts(vehicleId: string, includeArchived = false): Promise<VehiclePart[]> {
    const data = await apiClient.get<RecordLike[]>(`/vehicles/${vehicleId}/parts`, { query: { include_archived: includeArchived } })
    return data.map(mapVehiclePart)
  },
  async createVehiclePart(vehicleId: string, payload: VehiclePartPayload): Promise<VehiclePart> {
    return mapVehiclePart(await apiClient.post<RecordLike>(`/vehicles/${vehicleId}/parts`, { risk_level: 'unknown', risk_score: 0, status: 'unknown', ...payload }))
  },
  async updateVehiclePart(partId: string, payload: Partial<VehiclePartPayload>): Promise<VehiclePart> {
    return mapVehiclePart(await apiClient.put<RecordLike>(`/vehicles/parts/${partId}`, payload))
  },
  async archiveVehiclePart(partId: string, reason?: string): Promise<VehiclePart> {
    return mapVehiclePart(await apiClient.post<RecordLike>(`/vehicles/parts/${partId}/archive`, { reason }))
  },
  async restoreVehiclePart(partId: string): Promise<VehiclePart> {
    return mapVehiclePart(await apiClient.post<RecordLike>(`/vehicles/parts/${partId}/restore`, {}))
  },
  async listMaintenanceRecords(params: MaintenanceListParams = {}): Promise<MaintenanceRecord[]> {
    const [records, vehicles] = await Promise.all([
      apiClient.get<BackendList<RecordLike>>('/maintenance', { query: { page: 1, limit: 100, ...params } }),
      this.listVehicles(),
    ])
    return records.items.map((record) => mapMaintenanceRecord(record, vehicles))
  },
  async createMaintenanceRecord(payload: MaintenanceCreatePayload): Promise<MaintenanceRecord> {
    const data = await apiClient.post<RecordLike>('/maintenance', payload)
    const vehicles = await this.listVehicles()
    return mapMaintenanceRecord(data, vehicles)
  },
  async getMaintenanceRecord(recordId: string): Promise<MaintenanceRecord> {
    const [data, vehicles] = await Promise.all([apiClient.get<RecordLike>(`/maintenance/${recordId}`), this.listVehicles()])
    return mapMaintenanceRecord(data, vehicles)
  },
  async approveMaintenance(recordId: string): Promise<MaintenanceRecord> {
    const data = await apiClient.patch<RecordLike>(`/maintenance/${recordId}/approve`, {})
    return mapMaintenanceRecord(data, await this.listVehicles())
  },
  async startMaintenance(recordId: string): Promise<MaintenanceRecord> {
    const data = await apiClient.patch<RecordLike>(`/maintenance/${recordId}/start`, {})
    return mapMaintenanceRecord(data, await this.listVehicles())
  },
  async completeMaintenance(recordId: string, payload: MaintenanceCompletePayload): Promise<MaintenanceRecord> {
    const data = await apiClient.patch<RecordLike>(`/maintenance/${recordId}/complete`, payload)
    const vehicles = await this.listVehicles()
    return mapMaintenanceRecord(data, vehicles)
  },
  async updateMaintenance(recordId: string, payload: Partial<MaintenanceCreatePayload>): Promise<MaintenanceRecord> {
    const data = await apiClient.put<RecordLike>(`/maintenance/${recordId}`, payload)
    return mapMaintenanceRecord(data, await this.listVehicles())
  },
  async cancelMaintenance(recordId: string, reason: string): Promise<MaintenanceRecord> {
    const data = await apiClient.patch<RecordLike>(`/maintenance/${recordId}/cancel`, { reason })
    return mapMaintenanceRecord(data, await this.listVehicles())
  },
  async listAlerts(params: { alert_type?: string; severity?: string; status?: string; page?: number; limit?: number } = {}): Promise<Alert[]> {
    const data = await apiClient.get<BackendList<RecordLike>>('/alerts', { query: { page: 1, limit: 100, ...params } })
    return data.items.map(mapAlert)
  },
  async resolveAlert(alertId: string): Promise<Alert> {
    return mapAlert(await apiClient.patch<RecordLike>(`/alerts/${alertId}/resolve`))
  },
  async dismissAlert(alertId: string): Promise<Alert> {
    return mapAlert(await apiClient.patch<RecordLike>(`/alerts/${alertId}/dismiss`))
  },
  async getDashboardSummary(): Promise<RecordLike> {
    return apiClient.get<RecordLike>('/dashboard/fleet-summary')
  },
  async getHealthDistribution(): Promise<RecordLike> {
    return apiClient.get<RecordLike>('/dashboard/health-distribution')
  },
  async getRecentAlerts(limit = 5): Promise<Alert[]> {
    const data = await apiClient.get<RecordLike[]>('/dashboard/recent-alerts', { query: { limit } })
    return data.map(mapAlert)
  },
  async getPredictiveModelStatus(): Promise<RecordLike> {
    return apiClient.get<RecordLike>('/predictive-maintenance/model-status')
  },
  async listPredictions(params: { page?: number; limit?: number; risk_level?: string } = {}): Promise<BackendList<RecordLike>> {
    return apiClient.get<BackendList<RecordLike>>('/predictive-maintenance/predictions', { query: { page: 1, limit: 20, ...params } })
  },
  async getFleetRiskSummary(): Promise<RecordLike> {
    return apiClient.get<RecordLike>('/predictive-maintenance/fleet-risk-summary')
  },
  async recalculateMaintenanceRisk(vehicleId: string, options: { requestReview?: boolean } = {}): Promise<MaintenancePrediction> {
    return mapMaintenancePrediction(await apiClient.post<RecordLike>(`/predictive-maintenance/vehicles/${vehicleId}/recalculate`, { trigger: 'manual_recalculation', request_review: options.requestReview === true }))
  },
  async getAssessmentEligibility(vehicleId: string): Promise<AssessmentEligibility> {
    const raw = await apiClient.get<RecordLike>(`/predictive-maintenance/vehicles/${vehicleId}/eligibility`)
    const requirements = raw.requirements as RecordLike
    const profile = requirements.profile as RecordLike
    const commissioning = requirements.commissioning_inspection as RecordLike
    const trips = requirements.completed_trips as RecordLike
    const distance = requirements.recorded_distance_km as RecordLike
    const imported = requirements.imported_history as RecordLike
    const history = requirements.history_evidence as RecordLike
    return {
      vehicleId: String(raw.vehicle_id ?? vehicleId),
      onboardingType: raw.onboarding_type === 'brand_new' ? 'brand_new' : 'existing_fleet',
      eligible: raw.eligible === true,
      status: String(raw.status) as AssessmentEligibility['status'],
      hasNewData: raw.has_new_data === true,
      missingProfileFields: Array.isArray(raw.missing_profile_fields) ? raw.missing_profile_fields.map(String) : [],
      blockingReasons: Array.isArray(raw.blocking_reasons) ? raw.blocking_reasons.map(String) : [],
      requirements: {
        profile: { complete: profile?.complete === true },
        commissioningInspection: { complete: commissioning?.complete === true },
        completedTrips: { current: Number(trips?.current ?? 0), required: Number(trips?.required ?? 5), complete: trips?.complete === true },
        recordedDistanceKm: { current: Number(distance?.current ?? 0), required: Number(distance?.required ?? 100), complete: distance?.complete === true },
        importedHistory: { current: Number(imported?.current ?? 0), complete: imported?.complete === true },
        historyEvidence: { complete: history?.complete === true },
      },
    }
  },
  async createCommissioningInspection(vehicleId: string): Promise<VehicleMaintenanceInspection> {
    return this.createInspection({
      vehicle_id: vehicleId,
      inspection_type: 'commissioning',
      priority: 'medium',
      inspection_areas: ['General condition', 'Braking', 'Tires', 'Powertrain', 'Lights and warnings', 'Visible damage'],
      notes: 'Initial operational commissioning inspection',
    })
  },
  async downloadMaintenanceHistoryTemplate(vehicleId: string) {
    return apiClient.download('/maintenance/history/template', { query: { vehicle_id: vehicleId } })
  },
  async importMaintenanceHistory(vehicleId: string, workbook: File): Promise<{ imported_count: number; latest_service_date?: string }> {
    const formData = new FormData()
    formData.append('vehicle_id', vehicleId)
    formData.append('workbook', workbook)
    return apiClient.upload('/maintenance/history/import', formData)
  },
  async getCurrentMaintenancePrediction(vehicleId: string): Promise<MaintenancePrediction | null> {
    const data = await apiClient.get<RecordLike | null>(`/predictive-maintenance/vehicles/${vehicleId}/current`)
    return data ? mapMaintenancePrediction(data) : null
  },
  async getMaintenancePredictionHistory(vehicleId: string): Promise<MaintenancePrediction[]> {
    const data = await apiClient.get<BackendList<RecordLike> | RecordLike[]>(`/predictive-maintenance/vehicles/${vehicleId}/history`)
    return (Array.isArray(data) ? data : data.items).map(mapMaintenancePrediction)
  },
  async listMaintenancePredictions(params: { page?: number; limit?: number; risk_level?: string } = {}): Promise<MaintenancePrediction[]> {
    const data = await apiClient.get<BackendList<RecordLike>>('/predictive-maintenance/predictions', { query: { page: 1, limit: 100, ...params } })
    return data.items.map(mapMaintenancePrediction)
  },
  async listPredictionReviews(params: { status?: string; page?: number; limit?: number } = {}): Promise<MaintenanceReview[]> {
    const data = await apiClient.get<BackendList<RecordLike> | RecordLike[]>('/predictive-maintenance/reviews', { query: { page: 1, limit: 100, ...params } })
    return (Array.isArray(data) ? data : data.items).map(mapPredictionReview)
  },
  async resolvePredictionReview(reviewId: string, resolution: 'cleared' | 'confirmed', notes: string): Promise<MaintenanceReview> {
    return mapPredictionReview(await apiClient.post<RecordLike>(`/predictive-maintenance/reviews/${reviewId}/resolve`, { resolution, notes }))
  },
  async getSensorFreeModelStatus(): Promise<PredictiveModelStatus> {
    const raw = await apiClient.get<RecordLike>('/predictive-maintenance/model-status')
    return {
      available: raw.available === true, loaded: raw.loaded === true, degraded: raw.degraded === true,
      modelVersion: String(raw.model_version ?? ''), featureSchemaVersion: String(raw.feature_schema_version ?? ''),
      message: String(raw.message ?? raw.error ?? ''),
    }
  },
}
