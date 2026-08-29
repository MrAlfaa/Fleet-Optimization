import { apiClient } from './apiClient'
import type {
  LoadConsolidation,
  ConsolidationPlanningState,
  LoadEligibility,
  LoadJob,
  LoadPlan,
  ParcelConsolidation,
  LoadVehicleType,
  VehicleSuggestion,
} from '../features/loadOptimization/types'

export const loadOptimizationService = {
  eligibility(deliveryDate: string, deliveryPeriod: 'first_half' | 'second_half') {
    return apiClient.get<LoadEligibility>('/load-optimization/eligibility', { query: { delivery_date: deliveryDate, delivery_period: deliveryPeriod } })
  },
  consolidation(deliveryDate: string, deliveryPeriod: 'first_half' | 'second_half') {
    return apiClient.get<LoadConsolidation>('/load-optimization/consolidation', {
      query: { delivery_date: deliveryDate, delivery_period: deliveryPeriod },
    })
  },
  createConsolidation(payload: { delivery_date: string; delivery_period: 'first_half' | 'second_half'; seed?: number }) {
    return apiClient.post<{ reused: boolean; consolidation: ParcelConsolidation; exceptions: LoadEligibility['exceptions'] }>('/load-optimization/consolidations', payload)
  },
  listConsolidations(params: { delivery_date?: string; delivery_period?: string; status?: string; search?: string } = {}) {
    return apiClient.get<{ items: ParcelConsolidation[]; total: number }>('/load-optimization/consolidations', { query: params })
  },
  getConsolidation(consolidationId: string) {
    return apiClient.get<ParcelConsolidation>(`/load-optimization/consolidations/${consolidationId}`)
  },
  planningState(consolidationId: string) {
    return apiClient.get<ConsolidationPlanningState>(`/load-optimization/consolidations/${consolidationId}/planning-state`)
  },
  vehicleTypes() {
    return apiClient.get<{ items: LoadVehicleType[]; total: number }>('/load-optimization/vehicle-types')
  },
  createJob(payload: { delivery_date: string; delivery_period: 'first_half' | 'second_half'; order_ids?: string[]; consolidation_id?: string; seed?: number }) {
    return apiClient.post<{ reused: boolean; job: LoadJob | null; plan: LoadPlan | null; exceptions: LoadEligibility['exceptions'] }>('/load-optimization/jobs', payload)
  },
  getJob(jobId: string) {
    return apiClient.get<LoadJob>(`/load-optimization/jobs/${jobId}`)
  },
  cancelJob(jobId: string) {
    return apiClient.post<LoadJob>(`/load-optimization/jobs/${jobId}/cancel`)
  },
  listPlans(params: { delivery_date?: string; delivery_period?: string; status?: string; consolidation_id?: string } = {}) {
    return apiClient.get<{ items: LoadPlan[] }>('/load-optimization/plans', { query: params })
  },
  getPlan(planId: string) {
    return apiClient.get<LoadPlan>(`/load-optimization/plans/${planId}`)
  },
  approve(planId: string, optionId?: string) {
    return apiClient.post<LoadPlan>(`/load-optimization/plans/${planId}/approve`, { option_id: optionId })
  },
  suggestions(planId: string) {
    return apiClient.get<{ plan_id: string; suggestions: VehicleSuggestion[] }>(`/load-optimization/plans/${planId}/vehicle-suggestions`)
  },
  assign(planId: string, loadId: string, vehicleId: string) {
    return apiClient.post<LoadPlan>(`/load-optimization/plans/${planId}/loads/${loadId}/assign`, { vehicle_id: vehicleId })
  },
  release(planId: string) {
    return apiClient.post<LoadPlan>(`/load-optimization/plans/${planId}/release`)
  },
  export(planId: string) {
    return apiClient.download(`/load-optimization/plans/${planId}/export`)
  },
}
