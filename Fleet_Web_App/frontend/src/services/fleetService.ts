import type { Alert, EvPartCatalogItem, MaintenanceRecord, PaginatedResponse, Vehicle, VehiclePart } from '../types'
import { apiClient } from './apiClient'
import { mapAlert, mapMaintenanceRecord, mapVehicle, mapVehiclePart } from './adapters'

type BackendList<T> = PaginatedResponse<T>
type RecordLike = Record<string, unknown>

export interface VehicleCreatePayload {
  vehicle_code: string
  registration_number: string
  vehicle_type: string
  brand: string
  model: string
  year: number
  fuel_type?: string
  current_mileage?: number
  battery_capacity_kwh?: number
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

export const fleetService = {
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
      status: 'active',
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
  async listMaintenanceRecords(params: { vehicle_id?: string; page?: number; limit?: number } = {}): Promise<MaintenanceRecord[]> {
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
  async completeMaintenance(recordId: string, payload: { notes?: string; cost?: number; technician_name?: string } = {}): Promise<MaintenanceRecord> {
    const data = await apiClient.patch<RecordLike>(`/maintenance/${recordId}/complete`, payload)
    const vehicles = await this.listVehicles()
    return mapMaintenanceRecord(data, vehicles)
  },
  async updateMaintenance(recordId: string, payload: Partial<MaintenanceCreatePayload>): Promise<MaintenanceRecord> {
    const data = await apiClient.put<RecordLike>(`/maintenance/${recordId}`, payload)
    return mapMaintenanceRecord(data, await this.listVehicles())
  },
  async cancelMaintenance(recordId: string): Promise<MaintenanceRecord> {
    const data = await apiClient.patch<RecordLike>(`/maintenance/${recordId}/cancel`, {})
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
    return apiClient.get<RecordLike>('/predictive-maintenance/model/status')
  },
  async listPredictions(params: { page?: number; limit?: number; risk_level?: string } = {}): Promise<BackendList<RecordLike>> {
    return apiClient.get<BackendList<RecordLike>>('/predictive-maintenance/predictions', { query: { page: 1, limit: 20, ...params } })
  },
  async getFleetRiskSummary(): Promise<RecordLike> {
    return apiClient.get<RecordLike>('/predictive-maintenance/fleet-risk-summary')
  },
  async simulatePrediction(vehicleId: string): Promise<RecordLike> {
    return apiClient.post<RecordLike>(`/predictive-maintenance/simulate/${vehicleId}`)
  },
}
