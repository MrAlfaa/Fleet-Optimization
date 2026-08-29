import type { MaintenancePlanningWindow, MaintenancePrediction, RiskLevel } from '../../types'

export const VEHICLE_WORKSPACE_TABS = [
  { id: 'overview', label: 'Overview', permission: 'vehicles.tab.overview' },
  { id: 'risk-assessment', label: 'Risk Assessment', permission: 'vehicles.tab.risk_assessment' },
  { id: 'maintenance', label: 'Maintenance', permission: 'vehicles.tab.maintenance' },
  { id: 'parts-inspections', label: 'Parts & Inspections', permission: 'vehicles.tab.parts_inspections' },
  { id: 'activity', label: 'Activity', permission: 'vehicles.tab.activity' },
] as const

export type VehicleWorkspaceTab = (typeof VEHICLE_WORKSPACE_TABS)[number]['id']

export function resolveVehicleWorkspaceTab(value: string | null): VehicleWorkspaceTab {
  return VEHICLE_WORKSPACE_TABS.some((tab) => tab.id === value) ? value as VehicleWorkspaceTab : 'overview'
}

export function approvedAssessmentHistory(items: MaintenancePrediction[]) {
  return items
    .filter((item) => item.reviewStatus !== 'pending')
    .sort((left, right) => timestamp(right.createdAt) - timestamp(left.createdAt))
}

export function percentage(value: number) {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`
}

export function assessmentDate(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? 'Date unavailable'
    : new Intl.DateTimeFormat('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }).format(date)
}

export function planningRange(window: MaintenancePlanningWindow | null, status: string) {
  if (!window || status === 'no_near_term_failure_indicated') return 'No near-term service indicated'
  const ranges: string[] = []
  if (window.minimumDays !== undefined || window.maximumDays !== undefined) ranges.push(`${window.minimumDays ?? 0}-${window.maximumDays ?? 'open'} days`)
  if (window.minimumKm !== undefined || window.maximumKm !== undefined) ranges.push(`${number(window.minimumKm ?? 0)}-${number(window.maximumKm ?? 0)} km`)
  return ranges.join(' or ') || 'Planning range unavailable'
}

export function assessmentResult(risk: RiskLevel) {
  if (risk === 'low') return 'Ready for normal monitoring'
  if (risk === 'medium') return 'Monitor service condition'
  if (risk === 'high') return 'Inspection should be scheduled'
  return 'Service hold and engineering review required'
}

export function dataQualityLabel(value: string) {
  if (value === 'good') return 'Good coverage'
  if (value === 'fair') return 'Partial coverage'
  if (value === 'poor') return 'Limited coverage'
  return 'Coverage not confirmed'
}

function number(value: number) {
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(value)
}

function timestamp(value: string) {
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) ? parsed : 0
}
