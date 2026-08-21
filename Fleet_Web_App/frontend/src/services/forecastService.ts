import type { DemandForecast, DemandZone, OperationalZoneOption, PaginatedResponse } from '../types'
import { apiClient } from './apiClient'
import { mapDemandForecast, mapDemandZone } from './adapters'

type RecordLike = Record<string, unknown>

export const forecastService = {
  async listZones(params: { search?: string; page?: number; limit?: number } = {}): Promise<DemandZone[]> {
    const data = await apiClient.get<PaginatedResponse<RecordLike>>('/demand/zones', {
      query: { page: 1, limit: 100, ...params },
    })
    return data.items.map(mapDemandZone)
  },
  async listForecasts(params: { zone_id?: string; start_date?: string; end_date?: string; page?: number; limit?: number } = {}): Promise<DemandForecast[]> {
    const data = await apiClient.get<PaginatedResponse<RecordLike>>('/demand/forecasts', {
      query: { page: 1, limit: 100, ...params },
    })
    return data.items.map(mapDemandForecast)
  },
  async getOperationalZones(): Promise<OperationalZoneOption[]> {
    const data = await apiClient.get<{ items: RecordLike[] }>('/demand/operational-zones')
    return data.items.map((item) => ({
      id: String(item.operational_zone_id ?? item.zone_id),
      name: String(item.zone_display_name),
      latitude: Number(item.zone_lat),
      longitude: Number(item.zone_lng),
      serviceRadiusKm: Number(item.service_radius_km ?? 35),
    }))
  },
  async getForecastVsActual(params: { zone_id?: string; start_date?: string; end_date?: string } = {}): Promise<DemandForecast[]> {
    const data = await apiClient.get<{ items: RecordLike[] }>('/demand/forecast-vs-actual', { query: params })
    return data.items.map(mapDemandForecast)
  },
  async listActuals(params: { zone_id?: string; start_date?: string; end_date?: string } = {}) {
    return apiClient.get<{ items: RecordLike[] }>('/demand/actuals', { query: params })
  },
  async rebuildActuals() {
    return apiClient.post<RecordLike>('/demand/actuals/rebuild')
  },
  async listPlanningRecommendations(params: { zone_id?: string; page?: number; limit?: number } = {}) {
    return apiClient.get<PaginatedResponse<RecordLike>>('/demand/planning-recommendations', {
      query: { page: 1, limit: 100, ...params },
    })
  },
  async getTrend(): Promise<Array<{ day: string; actual: number; predicted: number }>> {
    const forecasts = await this.getForecastVsActual()
    return forecasts.slice(0, 7).map((forecast, index) => ({
      day: `Point ${index + 1}`,
      actual: forecast.currentVolume,
      predicted: forecast.predictedVolume,
    }))
  },
  async getModelStatus(): Promise<RecordLike> {
    return apiClient.get<RecordLike>('/demand/model/status')
  },
  async getModelMetrics(): Promise<RecordLike> {
    return apiClient.get<RecordLike>('/demand/model/metrics')
  },
  async getDashboardSummary(): Promise<RecordLike> {
    return apiClient.get<RecordLike>('/demand/dashboard-summary')
  },
  async importArtifacts(): Promise<RecordLike> {
    return apiClient.post<RecordLike>('/demand/import-artifacts')
  },
  async refreshForecast(days = 30, source: 'artifact' | 'model' = 'artifact'): Promise<RecordLike> {
    return apiClient.post<RecordLike>('/demand/refresh', {
      days,
      save_to_database: true,
      source,
    })
  },
  async getOperationalContext(date?: string) {
    return apiClient.get<{ date: string; holiday_name: string | null; is_holiday: boolean; rain_probability: number | null; weather_label: string; artifact_source: string; last_refresh_at: string | null }>('/operations/context', { query: { date } })
  },
  async exportForecast(params: { zone_id?: string; start_date?: string; end_date?: string } = {}) {
    return apiClient.download('/demand/export', { query: params })
  },
}
