import { CheckCircle2, Download, FileSpreadsheet, FileText, RotateCcw } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Card, PageHeader, PrimaryButton, SecondaryButton } from '../components/UI'
import { useDateRange } from '../hooks/useDateRange'
import { fleetService } from '../services/fleetService'
import { reportService, type ReportExportQuery, type SpecializedReportType } from '../services/reportService'
import { authService } from '../services/authService'
import { canAccess } from '../utils/permissions'
import type { Vehicle } from '../types'
import { saveDownload } from '../utils/download'
import { SRI_LANKA_ZONES } from '../data/sriLankaZones'

type VehicleCategory = NonNullable<ReportExportQuery['vehicle_category']>
type AssessmentResult = NonNullable<ReportExportQuery['assessment_result']>
type WorkflowStatus = NonNullable<ReportExportQuery['workflow_status']>
type InspectionStatus = NonNullable<ReportExportQuery['inspection_status']>
type DemandLevel = NonNullable<ReportExportQuery['demand_level']>
type RouteStatus = NonNullable<ReportExportQuery['route_status']>
type DeliveryPeriod = NonNullable<ReportExportQuery['delivery_period']>
type ConsolidationStatus = NonNullable<ReportExportQuery['consolidation_status']>
type DriverAccountStatus = NonNullable<ReportExportQuery['driver_account_status']>
type DeviceEnrollmentStatus = NonNullable<ReportExportQuery['device_enrollment_status']>

interface ReportDefinition {
  title: string
  description: string
  columns: string[]
}

const reportDefinitions: Record<SpecializedReportType, ReportDefinition> = {
  vehicle_maintenance: {
    title: 'Vehicle Maintenance Report',
    description: 'Review service risk, inspection state, maintenance activity, and recommended operational action by vehicle.',
    columns: ['Registration', 'Mileage', 'Assessment result', 'Failure risk', 'Planning range', 'Inspection status', 'Work order status', 'Recommended action'],
  },
  vehicle_details: {
    title: 'Vehicle Details Report',
    description: 'Export the fleet register with identity, category, fuel type, usage, capacity, and lifecycle status.',
    columns: ['Registration', 'Fleet code', 'Category', 'Fuel type', 'Mileage', 'Status', 'In-service date', 'Payload capacity'],
  },
  daily_inspection: {
    title: 'Daily Inspection Report',
    description: 'Review individual inspections, assigned personnel, elapsed time, checklist findings, and service decisions.',
    columns: ['Registration', 'Priority', 'Assigned to', 'Started', 'Completed', 'Duration', 'Checklist findings', 'Decision'],
  },
  inspection_summary: {
    title: 'Inspection Summary Report',
    description: 'Summarize inspection workload by status and priority for daily operational review.',
    columns: ['Status', 'Priority', 'Vehicle count', 'Pending', 'In progress', 'Completed', 'Service required', 'Returned to service'],
  },
  demand_forecast: {
    title: 'Zone Demand Forecast Report',
    description: 'Compare approved parcel demand, recorded orders, capacity requirements, and operational actions by zone and date.',
    columns: ['Forecast date', 'Zone', 'Recorded orders', 'Forecast orders', 'Variance', 'Demand level', 'Required vehicle shifts', 'Recommended action'],
  },
  demand_capacity: {
    title: 'Demand Capacity Summary Report',
    description: 'Summarize total, average, and peak parcel demand with the maximum vehicle capacity required for each zone.',
    columns: ['Zone', 'Forecast days', 'Total orders', 'Daily average', 'Peak demand', 'Peak date', 'High-demand days', 'Maximum vehicle shifts'],
  },
  route_optimization: {
    title: 'Route Optimization Report',
    description: 'Review route assignments, parcel stops, distance, planned duration, delay exposure, and dispatch progress.',
    columns: ['Route code', 'Delivery date', 'Period', 'Status', 'Vehicle', 'Driver', 'Parcel stops', 'Distance', 'Planned duration', 'Delay risk'],
  },
  route_stop_performance: {
    title: 'Route Stop Status Report',
    description: 'Inspect the ordered parcel stops and leg-level distance, duration, delivery status, and delay exposure for each route.',
    columns: ['Route code', 'Stop sequence', 'Order code', 'Zone', 'Priority', 'Parcel weight', 'Delivery status', 'Leg distance', 'Leg duration', 'Delay risk'],
  },
  consolidation_details: {
    title: 'Parcel Consolidation Report',
    description: 'Trace each consolidation from its planning batch to the included parcels, load plan, route set, and current workflow state.',
    columns: ['Consolidation ID', 'Delivery date', 'Period', 'Current status', 'Region', 'Order code', 'Parcel status', 'Planning state', 'Load plan', 'Route set'],
  },
  driver_details: {
    title: 'Driver Details Report',
    description: 'Review driver account availability, mobile enrollment, active assignment, and completed delivery workload.',
    columns: ['Driver', 'Username', 'Contact', 'Account status', 'Device enrollment', 'Assigned vehicle', 'Active route', 'Completed routes', 'Delivered parcels'],
  },
  route_details: {
    title: 'Route Details Report',
    description: 'Export the complete route handoff from consolidation and load plan through vehicle, driver, approval, and trip completion.',
    columns: ['Route code', 'Route set', 'Consolidation ID', 'Load plan', 'Load', 'Vehicle', 'Driver', 'Stops', 'Distance', 'Status', 'Approval', 'Dispatch'],
  },
}

const inputClass = 'mt-1.5 min-h-11 w-full rounded-lg border border-fleet-line bg-white px-3 py-2 text-sm font-medium text-fleet-ink outline-none transition focus:border-fleet-blue focus:ring-2 focus:ring-blue-100'
const labelClass = 'block min-w-0 text-xs font-bold uppercase tracking-wide text-fleet-muted'

function optionLabel(value: string) {
  return value.split('_').map((word) => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : 'The report could not be generated. Please try again.'
}

export function ReportsPage() {
  const canExport = canAccess(authService.getSession(), 'reports.export')
  const globalRange = useDateRange()
  const [reportType, setReportType] = useState<SpecializedReportType>('vehicle_maintenance')
  const [vehicles, setVehicles] = useState<Vehicle[]>([])
  const [vehicleLoading, setVehicleLoading] = useState(true)
  const [vehicleLoadError, setVehicleLoadError] = useState('')
  const [vehicleId, setVehicleId] = useState('')
  const [category, setCategory] = useState<VehicleCategory | ''>('')
  const [startDate, setStartDate] = useState(globalRange.start)
  const [endDate, setEndDate] = useState(globalRange.end)
  const [assessmentResult, setAssessmentResult] = useState<AssessmentResult | ''>('')
  const [workflowStatus, setWorkflowStatus] = useState<WorkflowStatus | ''>('')
  const [inspectionStatus, setInspectionStatus] = useState<InspectionStatus | ''>('')
  const [zoneId, setZoneId] = useState('')
  const [demandLevel, setDemandLevel] = useState<DemandLevel | ''>('')
  const [routeStatus, setRouteStatus] = useState<RouteStatus | ''>('')
  const [deliveryPeriod, setDeliveryPeriod] = useState<DeliveryPeriod | ''>('')
  const [consolidationId, setConsolidationId] = useState('')
  const [consolidationStatus, setConsolidationStatus] = useState<ConsolidationStatus | ''>('')
  const [driverAccountStatus, setDriverAccountStatus] = useState<DriverAccountStatus | ''>('')
  const [deviceEnrollmentStatus, setDeviceEnrollmentStatus] = useState<DeviceEnrollmentStatus | ''>('')
  const [exporting, setExporting] = useState<'specialized' | 'generic-pdf' | 'generic-xlsx' | null>(null)
  const [notice, setNotice] = useState<{ tone: 'success' | 'error'; message: string } | null>(null)

  useEffect(() => {
    let active = true
    fleetService.listVehicles({ limit: 100 })
      .then((items) => {
        if (active) setVehicles(items)
      })
      .catch((error: unknown) => {
        if (active) setVehicleLoadError(errorMessage(error))
      })
      .finally(() => {
        if (active) setVehicleLoading(false)
      })
    return () => { active = false }
  }, [])

  const definition = reportDefinitions[reportType]
  const dateInvalid = Boolean(startDate && endDate && startDate > endDate)
  const showMaintenanceFilters = reportType === 'vehicle_maintenance'
  const showInspectionFilter = ['vehicle_maintenance', 'daily_inspection', 'inspection_summary'].includes(reportType)
  const showDemandFilters = ['demand_forecast', 'demand_capacity'].includes(reportType)
  const showRouteFilters = ['route_optimization', 'route_stop_performance', 'route_details'].includes(reportType)
  const showConsolidationFilters = ['consolidation_details', 'route_details'].includes(reportType)
  const showDriverFilters = reportType === 'driver_details'
  const showDeliveryPeriodFilter = showRouteFilters || reportType === 'consolidation_details'
  const showVehicleFilter = ['vehicle_maintenance', 'vehicle_details', 'daily_inspection', 'inspection_summary', 'route_optimization', 'route_stop_performance', 'route_details'].includes(reportType)
  const showCategoryFilter = ['vehicle_maintenance', 'vehicle_details', 'daily_inspection', 'inspection_summary'].includes(reportType)
  const activeFilterCount = useMemo(
    () => [showVehicleFilter ? vehicleId : '', showCategoryFilter ? category : '', startDate, endDate,
      showMaintenanceFilters ? assessmentResult : '', showMaintenanceFilters ? workflowStatus : '',
      showInspectionFilter ? inspectionStatus : '', showDemandFilters ? zoneId : '', showDemandFilters ? demandLevel : '',
      showRouteFilters ? routeStatus : '', showDeliveryPeriodFilter ? deliveryPeriod : '',
      showConsolidationFilters ? consolidationId : '', reportType === 'consolidation_details' ? consolidationStatus : '',
      showDriverFilters ? driverAccountStatus : '', showDriverFilters ? deviceEnrollmentStatus : ''].filter(Boolean).length,
    [assessmentResult, category, consolidationId, consolidationStatus, deliveryPeriod, demandLevel, deviceEnrollmentStatus,
      driverAccountStatus, endDate, inspectionStatus, reportType, routeStatus, showCategoryFilter, showConsolidationFilters,
      showDemandFilters, showInspectionFilter, showMaintenanceFilters, showRouteFilters, showVehicleFilter, startDate, vehicleId,
      workflowStatus, zoneId, showDeliveryPeriodFilter, showDriverFilters],
  )

  const resetFilters = () => {
    setVehicleId('')
    setCategory('')
    setStartDate('')
    setEndDate('')
    setAssessmentResult('')
    setWorkflowStatus('')
    setInspectionStatus('')
    setZoneId('')
    setDemandLevel('')
    setRouteStatus('')
    setDeliveryPeriod('')
    setConsolidationId('')
    setConsolidationStatus('')
    setDriverAccountStatus('')
    setDeviceEnrollmentStatus('')
    setNotice(null)
  }

  const runExport = async (query: ReportExportQuery, state: NonNullable<typeof exporting>) => {
    if (exporting || dateInvalid) return
    setExporting(state)
    setNotice(null)
    try {
      const file = await reportService.export(query)
      saveDownload(file.blob, file.filename)
      setNotice({ tone: 'success', message: `${file.filename} is ready.` })
    } catch (error) {
      setNotice({ tone: 'error', message: errorMessage(error) })
    } finally {
      setExporting(null)
    }
  }

  const generateSpecializedReport = () => {
    const query: ReportExportQuery = {
      format: 'xlsx',
      report_type: reportType,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
      vehicle_id: showVehicleFilter ? vehicleId || undefined : undefined,
      vehicle_category: showCategoryFilter ? category || undefined : undefined,
    }
    if (showMaintenanceFilters) {
      query.assessment_result = assessmentResult || undefined
      query.workflow_status = workflowStatus || undefined
    }
    if (showInspectionFilter) query.inspection_status = inspectionStatus || undefined
    if (showDemandFilters) {
      query.zone_id = zoneId || undefined
      query.demand_level = demandLevel || undefined
    }
    if (showRouteFilters) {
      query.route_status = routeStatus || undefined
    }
    if (showDeliveryPeriodFilter) query.delivery_period = deliveryPeriod || undefined
    if (showConsolidationFilters) query.consolidation_id = consolidationId.trim() || undefined
    if (reportType === 'consolidation_details') query.consolidation_status = consolidationStatus || undefined
    if (showDriverFilters) {
      query.driver_account_status = driverAccountStatus || undefined
      query.device_enrollment_status = deviceEnrollmentStatus || undefined
    }
    void runExport(query, 'specialized')
  }

  const generateOperationalSummary = (format: 'pdf' | 'xlsx') => {
    void runExport({ format, start_date: startDate || undefined, end_date: endDate || undefined }, `generic-${format}`)
  }

  return (
    <div className="min-w-0 max-w-full">
      <PageHeader description="Build clear operational reports using only the vehicles, dates, and workflow states you need." title="Reports" />

      <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(300px,0.65fr)]">
        <section className="min-w-0 rounded-lg border border-fleet-line bg-white shadow-card">
          <div className="border-b border-fleet-line px-5 py-4">
            <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="text-base font-bold text-fleet-ink">Report Builder</h2>
                <p className="mt-1 text-sm text-fleet-muted">Choose a report and narrow the exported records when required.</p>
              </div>
              <span className="rounded-md bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700">{activeFilterCount} filters applied</span>
            </div>
          </div>

          <div className="space-y-6 p-5">
            <fieldset>
              <legend className="text-sm font-bold text-fleet-ink">Report type</legend>
              <div className="mt-3 grid gap-2 sm:grid-cols-2">
                {(Object.entries(reportDefinitions) as Array<[SpecializedReportType, ReportDefinition]>).map(([key, item]) => (
                  <label className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition ${reportType === key ? 'border-fleet-blue bg-blue-50/70 ring-1 ring-fleet-blue' : 'border-fleet-line hover:border-blue-300 hover:bg-slate-50'}`} key={key}>
                    <input checked={reportType === key} className="mt-1 h-4 w-4 accent-fleet-blue" name="report-type" onChange={() => setReportType(key)} type="radio" value={key} />
                    <span className="min-w-0">
                      <span className="block text-sm font-bold text-fleet-ink">{item.title}</span>
                      <span className="mt-0.5 block text-xs leading-5 text-fleet-muted">{item.description}</span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="grid min-w-0 gap-4 sm:grid-cols-2">
              {showVehicleFilter && <label className={labelClass}>Vehicle
                <select aria-label="Vehicle" className={inputClass} disabled={vehicleLoading} onChange={(event) => setVehicleId(event.target.value)} value={vehicleId}>
                  <option value="">All vehicles</option>
                  {vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.registrationNumber} · {vehicle.vehicleCode}</option>)}
                </select>
                {vehicleLoadError && <span className="mt-1 block normal-case tracking-normal text-red-600">Vehicle list unavailable. All vehicles can still be exported.</span>}
              </label>}
              {showCategoryFilter && <label className={labelClass}>Vehicle category
                <select aria-label="Vehicle category" className={inputClass} onChange={(event) => setCategory(event.target.value as VehicleCategory | '')} value={category}>
                  <option value="">All categories</option>
                  {(['car', 'van', 'truck', 'bus'] as const).map((value) => <option key={value} value={value}>{optionLabel(value)}</option>)}
                </select>
              </label>}
              <label className={labelClass}>Start date
                <input aria-label="Start date" className={inputClass} onChange={(event) => setStartDate(event.target.value)} type="date" value={startDate} />
              </label>
              <label className={labelClass}>End date
                <input aria-label="End date" className={inputClass} onChange={(event) => setEndDate(event.target.value)} min={startDate || undefined} type="date" value={endDate} />
              </label>

              {showMaintenanceFilters && <label className={labelClass}>Assessment result
                <select aria-label="Assessment result" className={inputClass} onChange={(event) => setAssessmentResult(event.target.value as AssessmentResult | '')} value={assessmentResult}>
                  <option value="">All results</option>
                  {(['low', 'medium', 'high', 'critical'] as const).map((value) => <option key={value} value={value}>{optionLabel(value)}</option>)}
                </select>
              </label>}
              {showMaintenanceFilters && <label className={labelClass}>Workflow status
                <select aria-label="Workflow status" className={inputClass} onChange={(event) => setWorkflowStatus(event.target.value as WorkflowStatus | '')} value={workflowStatus}>
                  <option value="">All workflow states</option>
                  {(['clear', 'service_hold', 'inspection', 'maintenance'] as const).map((value) => <option key={value} value={value}>{optionLabel(value)}</option>)}
                </select>
              </label>}
              {showInspectionFilter && <label className={labelClass}>Inspection status
                <select aria-label="Inspection status" className={inputClass} onChange={(event) => setInspectionStatus(event.target.value as InspectionStatus | '')} value={inspectionStatus}>
                  <option value="">All inspection states</option>
                  {(['pending', 'assigned', 'in_progress', 'completed', 'decision_pending', 'maintenance_required', 'maintenance_completed', 'returned_to_service', 'cancelled'] as const).map((value) => <option key={value} value={value}>{optionLabel(value)}</option>)}
                </select>
              </label>}
              {showDemandFilters && <label className={labelClass}>Operational zone
                <select aria-label="Operational zone" className={inputClass} onChange={(event) => setZoneId(event.target.value)} value={zoneId}>
                  <option value="">All Colombo zones</option>
                  {SRI_LANKA_ZONES.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}
                </select>
              </label>}
              {showDemandFilters && <label className={labelClass}>Demand level
                <select aria-label="Demand level" className={inputClass} onChange={(event) => setDemandLevel(event.target.value as DemandLevel | '')} value={demandLevel}>
                  <option value="">All demand levels</option>
                  {(['low', 'medium', 'high', 'very_high'] as const).map((value) => <option key={value} value={value}>{optionLabel(value)}</option>)}
                </select>
              </label>}
              {showRouteFilters && <label className={labelClass}>Route status
                <select aria-label="Route status" className={inputClass} onChange={(event) => setRouteStatus(event.target.value as RouteStatus | '')} value={routeStatus}>
                  <option value="">All route states</option>
                  {(['draft', 'optimized', 'approved', 'dispatched', 'in_progress', 'completed', 'cancelled'] as const).map((value) => <option key={value} value={value}>{optionLabel(value)}</option>)}
                </select>
              </label>}
              {showDeliveryPeriodFilter && <label className={labelClass}>Delivery period
                <select aria-label="Delivery period" className={inputClass} onChange={(event) => setDeliveryPeriod(event.target.value as DeliveryPeriod | '')} value={deliveryPeriod}>
                  <option value="">Both delivery periods</option>
                  <option value="first_half">First half</option>
                  <option value="second_half">Second half</option>
                </select>
              </label>}
              {showConsolidationFilters && <label className={labelClass}>Consolidation ID
                <input aria-label="Consolidation ID" className={inputClass} maxLength={40} onChange={(event) => setConsolidationId(event.target.value.toUpperCase())} placeholder="PCID202608291H001" value={consolidationId} />
              </label>}
              {reportType === 'consolidation_details' && <label className={labelClass}>Consolidation status
                <select aria-label="Consolidation status" className={inputClass} onChange={(event) => setConsolidationStatus(event.target.value as ConsolidationStatus | '')} value={consolidationStatus}>
                  <option value="">All consolidation states</option>
                  {(['active', 'planning', 'planned', 'approved', 'routed', 'superseded', 'failed', 'cancelled'] as const).map((value) => <option key={value} value={value}>{optionLabel(value)}</option>)}
                </select>
              </label>}
              {showDriverFilters && <label className={labelClass}>Driver account status
                <select aria-label="Driver account status" className={inputClass} onChange={(event) => setDriverAccountStatus(event.target.value as DriverAccountStatus | '')} value={driverAccountStatus}>
                  <option value="">All account states</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
              </label>}
              {showDriverFilters && <label className={labelClass}>Device enrollment
                <select aria-label="Device enrollment" className={inputClass} onChange={(event) => setDeviceEnrollmentStatus(event.target.value as DeviceEnrollmentStatus | '')} value={deviceEnrollmentStatus}>
                  <option value="">All enrollment states</option>
                  {(['pending', 'enrolled', 'revoked'] as const).map((value) => <option key={value} value={value}>{optionLabel(value)}</option>)}
                </select>
              </label>}
            </div>

            {dateInvalid && <p aria-live="polite" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">Start date must be on or before the end date.</p>}

            <div className="flex flex-col-reverse gap-2 border-t border-fleet-line pt-5 sm:flex-row sm:items-center sm:justify-between">
              <SecondaryButton disabled={exporting !== null || activeFilterCount === 0} onClick={resetFilters}><RotateCcw className="h-4 w-4" />Reset filters</SecondaryButton>
              {canExport && <PrimaryButton disabled={exporting !== null || dateInvalid} onClick={generateSpecializedReport}><Download className="h-4 w-4" />{exporting === 'specialized' ? 'Generating Excel...' : 'Generate Excel'}</PrimaryButton>}
            </div>
          </div>
        </section>

        <aside className="min-w-0 space-y-5">
          <section className="rounded-lg border border-fleet-line bg-white p-5 shadow-card">
            <div className="flex items-start gap-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-emerald-50 text-emerald-700"><FileSpreadsheet className="h-5 w-5" /></span>
              <div className="min-w-0">
                <h2 className="text-base font-bold text-fleet-ink">{definition.title}</h2>
                <p className="mt-1 text-sm leading-6 text-fleet-muted">{definition.description}</p>
              </div>
            </div>
            <div className="mt-5 border-t border-fleet-line pt-4">
              <h3 className="text-xs font-bold uppercase tracking-wide text-fleet-muted">Column preview</h3>
              <ul className="mt-3 grid gap-x-4 gap-y-2 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
                {definition.columns.map((column) => <li className="flex min-w-0 items-center gap-2 text-sm font-medium text-fleet-ink" key={column}><CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />{column}</li>)}
              </ul>
            </div>
          </section>

          {notice && <div aria-live="polite" className={`rounded-lg border p-4 text-sm font-semibold ${notice.tone === 'success' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-700'}`} role={notice.tone === 'error' ? 'alert' : 'status'}>{notice.message}</div>}
        </aside>
      </div>

      <div className="mt-5">
        <Card title="Operational Summary">
          <div className="flex min-w-0 flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              <div className="flex items-center gap-2 font-bold text-fleet-ink"><FileText className="h-5 w-5 text-fleet-blue" />Management overview</div>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-fleet-muted">Download the broader fleet, maintenance, demand, routes, deliveries, and alerts summary. The selected date range is applied when provided.</p>
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              {canExport && <><SecondaryButton disabled={exporting !== null || dateInvalid} onClick={() => generateOperationalSummary('pdf')}><Download className="h-4 w-4" />{exporting === 'generic-pdf' ? 'Generating PDF...' : 'Download PDF'}</SecondaryButton><SecondaryButton disabled={exporting !== null || dateInvalid} onClick={() => generateOperationalSummary('xlsx')}><Download className="h-4 w-4" />{exporting === 'generic-xlsx' ? 'Generating Excel...' : 'Download Excel'}</SecondaryButton></>}
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
