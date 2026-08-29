import { apiClient } from './apiClient'

export type SpecializedReportType =
  | 'vehicle_maintenance'
  | 'vehicle_details'
  | 'daily_inspection'
  | 'inspection_summary'
  | 'demand_forecast'
  | 'demand_capacity'
  | 'route_optimization'
  | 'route_stop_performance'
  | 'consolidation_details'
  | 'driver_details'
  | 'route_details'

export interface ReportExportQuery {
  format: 'pdf' | 'xlsx'
  report_type?: SpecializedReportType
  start_date?: string
  end_date?: string
  vehicle_id?: string
  vehicle_category?: 'car' | 'van' | 'truck' | 'bus'
  assessment_result?: 'low' | 'medium' | 'high' | 'critical'
  workflow_status?: 'clear' | 'service_hold' | 'inspection' | 'maintenance'
  inspection_status?: 'pending' | 'assigned' | 'in_progress' | 'completed' | 'decision_pending' | 'maintenance_required' | 'maintenance_completed' | 'returned_to_service' | 'cancelled'
  zone_id?: string
  demand_level?: 'low' | 'medium' | 'high' | 'very_high'
  route_status?: 'draft' | 'optimized' | 'approved' | 'dispatched' | 'in_progress' | 'completed' | 'cancelled'
  delivery_period?: 'first_half' | 'second_half'
  consolidation_id?: string
  consolidation_status?: 'active' | 'planning' | 'planned' | 'approved' | 'routed' | 'superseded' | 'failed' | 'cancelled'
  driver_id?: string
  driver_account_status?: 'active' | 'inactive'
  device_enrollment_status?: 'pending' | 'enrolled' | 'revoked'
}

function exportReport(query: ReportExportQuery): ReturnType<typeof apiClient.download>
function exportReport(format: 'pdf' | 'xlsx', start_date?: string, end_date?: string): ReturnType<typeof apiClient.download>
function exportReport(queryOrFormat: ReportExportQuery | 'pdf' | 'xlsx', start_date?: string, end_date?: string) {
  const query = typeof queryOrFormat === 'string'
    ? { format: queryOrFormat, start_date, end_date }
    : queryOrFormat
  return apiClient.download('/reports/export', { query: { ...query } })
}

export const reportService = {
  export: exportReport,
}
