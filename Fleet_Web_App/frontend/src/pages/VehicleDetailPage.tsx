import { CalendarClock, CalendarDays, CarFront, CheckCircle2, ClipboardCheck, FileSpreadsheet, Fuel, Gauge, Info, Plus, RefreshCw, ShieldAlert, UserRound, Weight, Wrench } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import clsx from 'clsx'
import { DataTable, EmptyState, ErrorState, LoadingState, PrimaryButton, RiskBadge, SecondaryButton, StatusBadge } from '../components/UI'
import { VehicleIdentity } from '../components/VehicleIdentity'
import { VehicleComponentDialog } from '../components/VehicleComponentDialog'
import { MaintenanceRecordDialog } from '../components/MaintenanceRecordDialog'
import { AddInspectionDialog } from '../components/AddInspectionDialog'
import { MaintenanceHistoryImportDialog } from '../components/MaintenanceHistoryImportDialog'
import { useAsyncData } from '../hooks/useAsyncData'
import { fleetService } from '../services/fleetService'
import { authService } from '../services/authService'
import { showToast } from '../utils/toast'
import { canAccess } from '../utils/permissions'
import {
  approvedAssessmentHistory, assessmentDate, assessmentResult, dataQualityLabel, percentage, planningRange,
  resolveVehicleWorkspaceTab, VEHICLE_WORKSPACE_TABS,
} from '../features/maintenance/assessmentView'
import type { AssessmentEligibility, MaintenancePrediction, MaintenanceRecord, Vehicle, VehicleMaintenanceInspection, VehiclePart } from '../types'

export function VehicleDetailPage() {
  const { vehicleId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const currentUser = authService.getSession()
  const requestedTab = resolveVehicleWorkspaceTab(searchParams.get('tab'))
  const availableTabs = VEHICLE_WORKSPACE_TABS.filter((tab) => canAccess(currentUser, tab.permission))
  const activeTab = availableTabs.some((tab) => tab.id === requestedTab) ? requestedTab : availableTabs[0]?.id
  const [selectedPart, setSelectedPart] = useState<VehiclePart | null>(null)
  const [showPartDialog, setShowPartDialog] = useState(false)
  const [maintenancePart, setMaintenancePart] = useState<VehiclePart | null>(null)
  const [editingRecord, setEditingRecord] = useState<MaintenanceRecord | null>(null)
  const [showMaintenance, setShowMaintenance] = useState(false)
  const [assessing, setAssessing] = useState(false)
  const [showInspectionDialog, setShowInspectionDialog] = useState(false)
  const [inspectionAdded, setInspectionAdded] = useState(false)
  const [showHistoryImport, setShowHistoryImport] = useState(false)
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [vehicle, parts, maintenanceRecords, assessment, assessmentHistory, inspectionPage, eligibility] = await Promise.all([
      fleetService.getVehicle(vehicleId),
      fleetService.listVehicleParts(vehicleId, true),
      fleetService.listMaintenanceRecords({ vehicle_id: vehicleId }),
      fleetService.getCurrentMaintenancePrediction(vehicleId).catch(() => null),
      fleetService.getMaintenancePredictionHistory(vehicleId).catch(() => []),
      fleetService.listInspections({ vehicle_id: vehicleId }).catch(() => ({ items: [], page: 1, limit: 100, total: 0, pages: 0 })),
      fleetService.getAssessmentEligibility(vehicleId),
    ])
    return { vehicle, parts, maintenanceRecords, assessment, assessmentHistory, inspections: inspectionPage.items, eligibility }
  }, [vehicleId])

  if (loading) return <LoadingState label="Loading vehicle workspace..." />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load vehicle workspace'} onRetry={reload} />

  const { vehicle, parts, maintenanceRecords, assessment, assessmentHistory, inspections, eligibility } = data
  const history = approvedAssessmentHistory(assessmentHistory)
  const activeParts = parts.filter((item) => item.isActive !== false)
  const activeInspection = inspections.find((item) => item.isActive)
  const canManageMaintenance = canAccess(currentUser, 'maintenance.manage')
  const canRunAssessment = canAccess(currentUser, 'predictive.run')
  const canUpdateVehicle = canAccess(currentUser, 'vehicles.update')
  const canManageInspections = canManageMaintenance
  const assessmentCanRun = eligibility.eligible && eligibility.status !== 'assessment_current'

  if (!activeTab) return <ErrorState message="No vehicle workspace tabs are assigned to your account." />

  const selectTab = (tab: string) => {
    const next = new URLSearchParams(searchParams)
    if (tab === 'overview') next.delete('tab')
    else next.set('tab', tab)
    setSearchParams(next, { replace: true })
  }

  const createAssessment = async () => {
    if (!assessmentCanRun) return
    setAssessing(true)
    try {
      await fleetService.recalculateMaintenanceRisk(vehicle.id)
      await reload()
      showToast({ tone: 'success', title: 'Assessment updated', message: 'The latest vehicle usage and service records were reviewed.' })
    } catch (reason) {
      showToast({ tone: 'error', title: 'Assessment could not be created', message: reason instanceof Error ? reason.message : 'Review the vehicle details and try again.' })
    } finally {
      setAssessing(false)
    }
  }

  const startCommissioning = async () => {
    setAssessing(true)
    try {
      await fleetService.createCommissioningInspection(vehicle.id)
      setInspectionAdded(true)
      await reload()
      showToast({ tone: 'success', title: 'Initial inspection created', message: 'The vehicle is now available in the inspection queue.' })
    } catch (reason) {
      showToast({ tone: 'error', title: 'Inspection could not be created', message: reason instanceof Error ? reason.message : 'Try again.' })
    } finally {
      setAssessing(false)
    }
  }

  return <div className="min-w-0 space-y-5">
    <section className="flex min-w-0 flex-col gap-5 rounded-lg border border-slate-200 bg-white p-5 shadow-card lg:flex-row lg:items-center lg:justify-between">
      <VehicleIdentity size="lg" vehicle={vehicle} />
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge tone={vehicle.status === 'Active' ? 'green' : vehicle.status === 'Maintenance' ? 'amber' : 'slate'}>{vehicle.status}</StatusBadge>
        <RiskBadge risk={assessment?.risk ?? vehicle.risk} />
        {canRunAssessment && activeTab !== 'risk-assessment' && <SecondaryButton disabled={assessing || !assessmentCanRun} onClick={createAssessment}>
          <RefreshCw className={clsx('h-4 w-4', assessing && 'animate-spin motion-reduce:animate-none')} />
          {assessing ? 'Creating Assessment...' : 'Create New Assessment'}
        </SecondaryButton>}
      </div>
    </section>

    {assessment?.dispatchHold && <section className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
      <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" />
      <div><div className="font-extrabold">Service hold is active</div><p className="mt-1 font-medium text-red-700">This vehicle cannot be dispatched until the required review or service work is completed.</p></div>
    </section>}

    <nav aria-label="Vehicle workspace" className="min-w-0 overflow-x-auto rounded-lg border border-slate-200 bg-white p-1 shadow-sm" role="tablist">
      <div className="flex min-w-max gap-1">
        {availableTabs.map((tab) => <button
          aria-controls={`vehicle-tab-${tab.id}`}
          aria-selected={activeTab === tab.id}
          className={clsx('min-h-10 rounded-md px-4 text-sm font-semibold transition', activeTab === tab.id ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100')}
          id={`vehicle-tab-button-${tab.id}`}
          key={tab.id}
          onClick={() => selectTab(tab.id)}
          role="tab"
          type="button"
        >{tab.label}</button>)}
      </div>
    </nav>

    <div aria-labelledby={`vehicle-tab-button-${activeTab}`} id={`vehicle-tab-${activeTab}`} role="tabpanel">
      {activeTab === 'overview' && <OverviewTab assessment={assessment} records={maintenanceRecords} vehicle={vehicle} />}
      {activeTab === 'risk-assessment' && <AssessmentTab assessment={assessment} activeInspection={activeInspection} canManageInspections={canManageInspections} canRunAssessment={canRunAssessment} eligibility={eligibility} history={history} inspectionAdded={inspectionAdded} onAddInspection={() => setShowInspectionDialog(true)} onCreate={createAssessment} onImportHistory={() => setShowHistoryImport(true)} onStartCommissioning={startCommissioning} working={assessing} />}
      {activeTab === 'maintenance' && <MaintenanceTab canImport={canManageMaintenance && vehicle.onboardingType === 'existing_fleet'} canManage={canManageMaintenance} onCreate={() => setShowMaintenance(true)} onEdit={setEditingRecord} onImport={() => setShowHistoryImport(true)} records={maintenanceRecords} vehicle={vehicle} />}
      {activeTab === 'parts-inspections' && <PartsTab canManage={canUpdateVehicle} inspections={inspections} onAdd={() => setShowPartDialog(true)} onSelect={setSelectedPart} parts={activeParts} />}
      {activeTab === 'activity' && <ActivityTab assessments={history} records={maintenanceRecords} />}
    </div>

    {(showPartDialog || selectedPart) && <VehicleComponentDialog
      canManage={canUpdateVehicle}
      onClose={() => { setShowPartDialog(false); setSelectedPart(null) }}
      onCreateMaintenance={canManageMaintenance ? (part) => { setSelectedPart(null); setMaintenancePart(part) } : undefined}
      onSaved={reload}
      part={selectedPart}
      parts={parts}
      vehicleId={vehicle.id}
    />}
    {(showMaintenance || maintenancePart || editingRecord) && <MaintenanceRecordDialog
      onClose={() => { setShowMaintenance(false); setMaintenancePart(null); setEditingRecord(null) }}
      onSaved={reload}
      part={maintenancePart}
      record={editingRecord}
      vehicle={vehicle}
    />}
    {showInspectionDialog && assessment && <AddInspectionDialog assessment={assessment} onClose={() => setShowInspectionDialog(false)} onCreated={async () => { setInspectionAdded(true); await reload() }} vehicle={vehicle} />}
    {showHistoryImport && <MaintenanceHistoryImportDialog onClose={() => setShowHistoryImport(false)} onImported={reload} vehicle={vehicle} />}
  </div>
}

function OverviewTab({ vehicle, assessment, records }: { vehicle: Vehicle; assessment: MaintenancePrediction | null; records: MaintenanceRecord[] }) {
  const open = records.filter((record) => !['Completed', 'Cancelled'].includes(record.status))
  return <div className="space-y-5">
    <section className="grid overflow-hidden rounded-lg border border-slate-200 bg-white sm:grid-cols-2 xl:grid-cols-4">
      <Summary label="Assessment result" value={assessment ? assessmentResult(assessment.risk) : 'Assessment required'} />
      <Summary label="Current mileage" value={`${new Intl.NumberFormat().format(vehicle.mileage)} km`} />
      <Summary label="Open service work" value={String(open.length)} />
      <Summary label="Data quality" value={assessment ? dataQualityLabel(assessment.dataQuality) : 'Not assessed'} />
    </section>
    <div className="grid min-w-0 gap-5 lg:grid-cols-[minmax(0,1.25fr)_minmax(280px,0.75fr)]">
      <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-card">
        <div className="border-b border-slate-200 bg-gradient-to-r from-blue-50 via-white to-emerald-50 px-5 py-4">
          <h2 className="font-extrabold text-slate-950">Vehicle profile</h2>
          <p className="mt-1 text-sm text-slate-500">Core operating details used for readiness and service planning.</p>
        </div>
        <div className="grid gap-3 p-5 sm:grid-cols-2 xl:grid-cols-3">
          <ProfileDetail icon={CarFront} label="Category" tone="blue" value={vehicle.vehicleCategory ?? vehicle.category} />
          <ProfileDetail icon={Fuel} label="Fuel type" tone="emerald" value={vehicle.fuelType ?? 'Not recorded'} />
          <ProfileDetail icon={CalendarDays} label="In-service date" tone="violet" value={vehicle.inServiceDate ?? 'Not recorded'} />
          <ProfileDetail icon={Weight} label="Payload capacity" tone="amber" value={vehicle.payloadCapacityKg ? `${new Intl.NumberFormat().format(vehicle.payloadCapacityKg)} kg` : 'Not recorded'} />
          <ProfileDetail icon={Wrench} label="Brand and type" tone="cyan" value={`${vehicle.brand ?? ''} ${vehicle.modelName ?? vehicle.model}`.trim()} />
          <ProfileDetail icon={UserRound} label="Assigned driver" tone="rose" value={vehicle.assignedDriver} />
        </div>
      </section>
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
        <h2 className="font-extrabold text-slate-950">Operational readiness</h2>
        <div className="mt-4 flex items-start gap-3 rounded-lg bg-slate-50 p-4">
          <CheckCircle2 className={clsx('mt-0.5 h-5 w-5 shrink-0', assessment?.dispatchHold ? 'text-red-600' : 'text-emerald-600')} />
          <div><div className="font-bold text-slate-950">{assessment?.dispatchHold ? 'Dispatch blocked' : 'No assessment hold'}</div><p className="mt-1 text-sm text-slate-600">Vehicle, inspection, and service rules are checked again before dispatch.</p></div>
        </div>
      </section>
    </div>
  </div>
}

function AssessmentTab({ assessment, eligibility, history, onCreate, working, activeInspection, canManageInspections, canRunAssessment, onAddInspection, onStartCommissioning, onImportHistory, inspectionAdded }: { assessment: MaintenancePrediction | null; eligibility: AssessmentEligibility; history: MaintenancePrediction[]; onCreate: () => void; working: boolean; activeInspection?: VehicleMaintenanceInspection; canManageInspections: boolean; canRunAssessment: boolean; onAddInspection: () => void; onStartCommissioning: () => void; onImportHistory: () => void; inspectionAdded: boolean }) {
  const canCreate = eligibility.eligible && eligibility.status !== 'assessment_current'
  const needsCommissioning = eligibility.status === 'commissioning_required'
  const needsImportedHistory = eligibility.status === 'building_history' && eligibility.onboardingType === 'existing_fleet'
  return <div className="space-y-5">
    <section className="rounded-lg border border-slate-200 bg-white shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 p-5">
        <div><h2 className="text-xl font-extrabold text-slate-950">Vehicle Risk Assessment</h2><p className="mt-1 max-w-3xl text-sm text-slate-600">Review near-term service risk, priority inspection areas, and whether this vehicle is ready for dispatch. Reassess after mileage, trip, inspection, or service records are updated.</p></div>
        <div className="flex flex-wrap gap-2">
          {assessment && canManageInspections && !activeInspection && <SecondaryButton onClick={onAddInspection}><ClipboardCheck className="h-4 w-4" />Add to Inspection</SecondaryButton>}
          {needsCommissioning && canManageInspections && !activeInspection && <SecondaryButton disabled={working} onClick={onStartCommissioning}><ClipboardCheck className="h-4 w-4" />Start Initial Inspection</SecondaryButton>}
          {needsImportedHistory && canManageInspections && <SecondaryButton onClick={onImportHistory}><FileSpreadsheet className="h-4 w-4" />Import Service History</SecondaryButton>}
          {canRunAssessment && <PrimaryButton disabled={working || !canCreate} onClick={onCreate}><RefreshCw className={clsx('h-4 w-4', working && 'animate-spin')} />Create New Assessment</PrimaryButton>}
        </div>
      </div>
      {(inspectionAdded || activeInspection) && <div className="flex flex-wrap items-center justify-between gap-3 border-b border-blue-200 bg-blue-50 px-5 py-3 text-sm font-semibold text-blue-800"><span>{inspectionAdded ? 'This vehicle was added to the inspection queue.' : `Active inspection: ${activeInspection?.status.replaceAll('_', ' ')}`}</span><Link className="font-extrabold hover:underline" to="/maintenance/inspections">Open Inspection Queue</Link></div>}
      {!eligibility.eligible && <AssessmentReadiness eligibility={eligibility} />}
      {assessment ? <div className="p-5">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <AssessmentMetric icon={Gauge} label="30-day service risk" value={percentage(assessment.probability30Days)} />
          <AssessmentMetric icon={Gauge} label="2,000-km service risk" value={percentage(assessment.probability2000Km)} />
          <AssessmentMetric icon={CalendarClock} label="Maintenance planning range" value={planningRange(assessment.planningWindow, assessment.planningStatus)} />
          <AssessmentMetric icon={ClipboardCheck} label="Data quality" value={dataQualityLabel(assessment.dataQuality)} />
        </div>
        <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(260px,0.6fr)]">
          <div><h3 className="text-sm font-extrabold text-slate-950">Inspection priority areas</h3><div className="mt-3 flex flex-wrap gap-2">{assessment.systemRisks.length ? assessment.systemRisks.slice(0, 3).map((item) => <span className="rounded-md bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-700" key={item.key}>{item.name} · {percentage(item.probability)}</span>) : <span className="text-sm text-slate-500">No priority areas identified.</span>}</div></div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4"><div className="text-xs font-bold uppercase text-slate-500">Assessment result</div><div className="mt-2 font-extrabold text-slate-950">{assessmentResult(assessment.risk)}</div><div className="mt-3"><RiskBadge risk={assessment.risk} /></div></div>
        </div>
      </div> : <div className="p-5"><EmptyState description="Create the first assessment using recorded mileage, operations, inspections, and service history." title="No assessment available" /></div>}
    </section>
    <section className="rounded-lg border border-slate-200 bg-white shadow-card">
      <div className="border-b border-slate-200 p-5"><h2 className="font-extrabold text-slate-950">Approved assessment history</h2><p className="mt-1 text-sm text-slate-500">Only accepted operational results are listed here.</p></div>
      {history.length ? <div className="divide-y divide-slate-200">{history.map((item) => <div className="flex flex-wrap items-center justify-between gap-4 p-5" key={item.id}><div><div className="font-bold text-slate-950">{assessmentDate(item.createdAt)}</div><div className="mt-1 text-sm text-slate-500">30-day service risk {percentage(item.probability30Days)} · 2,000-km service risk {percentage(item.probability2000Km)}</div></div><div className="flex items-center gap-2"><StatusBadge tone="green">Approved</StatusBadge><RiskBadge risk={item.risk} /></div></div>)}</div> : <div className="p-5"><EmptyState description="Approved results remain here as read-only operational history." title="No approved history" /></div>}
    </section>
  </div>
}

function AssessmentReadiness({ eligibility }: { eligibility: AssessmentEligibility }) {
  const title = eligibility.status === 'profile_incomplete'
    ? 'Complete vehicle profile'
    : eligibility.status === 'commissioning_required'
      ? 'Initial inspection required'
      : 'Build service history'
  const items = eligibility.onboardingType === 'brand_new'
    ? [
      { label: 'Vehicle profile', complete: eligibility.requirements.profile.complete },
      { label: 'Initial inspection', complete: eligibility.requirements.commissioningInspection.complete },
      { label: `${eligibility.requirements.completedTrips.current} of ${eligibility.requirements.completedTrips.required} completed trips`, complete: eligibility.requirements.completedTrips.complete },
      { label: `${eligibility.requirements.recordedDistanceKm.current} of ${eligibility.requirements.recordedDistanceKm.required} km recorded`, complete: eligibility.requirements.recordedDistanceKm.complete },
    ]
    : [
      { label: 'Vehicle profile', complete: eligibility.requirements.profile.complete },
      { label: 'Initial inspection', complete: eligibility.requirements.commissioningInspection.complete },
      { label: `${eligibility.requirements.importedHistory.current} imported completed service record(s)`, complete: eligibility.requirements.importedHistory.complete },
    ]
  return <div className="border-b border-amber-200 bg-amber-50 p-5">
    <div className="flex items-start gap-3"><ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" /><div className="min-w-0"><h3 className="font-extrabold text-amber-950">{title}</h3><p className="mt-1 text-sm text-amber-800">The first risk assessment becomes available only after the required operating evidence is recorded.</p></div></div>
    <div className="mt-4 grid gap-2 sm:grid-cols-2">{items.map((item) => <div className="flex items-center gap-2 rounded-lg border border-amber-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700" key={item.label}><CheckCircle2 className={clsx('h-4 w-4', item.complete ? 'text-emerald-600' : 'text-slate-300')} />{item.label}</div>)}</div>
    {eligibility.blockingReasons.length > 0 && <p className="mt-3 text-sm font-semibold text-amber-900">Next: {eligibility.blockingReasons.join('. ')}</p>}
  </div>
}

function MaintenanceTab({ records, vehicle, onCreate, onEdit, onImport, canImport, canManage }: { records: MaintenanceRecord[]; vehicle: Vehicle; onCreate: () => void; onEdit: (record: MaintenanceRecord) => void; onImport: () => void; canImport: boolean; canManage: boolean }) {
  return <section className="rounded-lg border border-slate-200 bg-white shadow-card">
    <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-5"><div><h2 className="text-lg font-extrabold text-slate-950">Service records</h2><p className="mt-1 text-sm text-slate-500">Open and completed work for {vehicle.registrationNumber}.</p></div>{canManage && <div className="flex flex-wrap gap-2">{canImport && <SecondaryButton onClick={onImport}><FileSpreadsheet className="h-4 w-4" />Import History</SecondaryButton>}<PrimaryButton onClick={onCreate}><Plus className="h-4 w-4" />Create Service Record</PrimaryButton></div>}</div>
    {records.length ? <div className="p-5"><DataTable headers={['Date', 'Service', 'Priority', 'Technician', 'Cost', 'Status', 'Action']}>{records.map((record) => <tr key={record.id}><td className="px-5 py-4 font-bold">{record.date}</td><td className="px-5 py-4"><div className="font-bold">{record.service}</div><div className="text-xs text-slate-500">{record.partName}</div></td><td className="px-5 py-4 capitalize">{record.priority}</td><td className="px-5 py-4">{record.technician}</td><td className="px-5 py-4 font-semibold">{record.actualCost == null ? record.cost : `LKR ${record.actualCost.toLocaleString()}`}</td><td className="px-5 py-4"><StatusBadge tone={record.workOrderStatus === 'completed' || record.status === 'Completed' ? 'green' : record.workOrderStatus === 'cancelled' || record.status === 'Cancelled' ? 'slate' : record.status === 'Overdue' ? 'red' : record.workOrderStatus === 'in_progress' ? 'blue' : 'amber'}>{(record.workOrderStatus ?? record.status).replaceAll('_', ' ')}</StatusBadge></td><td className="px-5 py-4">{record.workOrderStatus ? <Link className="rounded-md px-3 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50" to={`/maintenance/work-orders?workOrderId=${record.id}`}>Open work order</Link> : <button className="rounded-md px-3 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50 disabled:text-slate-400" disabled={['Completed', 'Cancelled'].includes(record.status)} onClick={() => onEdit(record)} type="button">Edit record</button>}</td></tr>)}</DataTable></div> : <div className="p-5"><EmptyState description="Service activity remains attached to this vehicle." title="No service records" /></div>}
  </section>
}

function PartsTab({ parts, inspections, onAdd, onSelect, canManage }: { parts: VehiclePart[]; inspections: VehicleMaintenanceInspection[]; onAdd: () => void; onSelect: (part: VehiclePart) => void; canManage: boolean }) {
  return <div className="space-y-5">
    <section className="rounded-lg border border-slate-200 bg-white shadow-card">
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-200 p-5"><div><h2 className="text-lg font-extrabold text-slate-950">Optional service inventory</h2><p className="mt-1 max-w-3xl text-sm text-slate-500">Parts are tracked only when the service team needs item-level history. Vehicle assessment does not require a fixed part list.</p></div>{canManage && <SecondaryButton onClick={onAdd}><Plus className="h-4 w-4" />Add Part</SecondaryButton>}</div>
      {parts.length ? <div className="grid gap-3 p-5 md:grid-cols-2 xl:grid-cols-3">{parts.map((part) => <button className="rounded-lg border border-slate-200 p-4 text-left transition hover:border-blue-300 hover:bg-blue-50/50" key={part.id} onClick={() => onSelect(part)} type="button"><div className="flex items-center justify-between gap-3"><span className="truncate font-extrabold text-slate-950">{part.name}</span><StatusBadge tone={part.status === 'healthy' ? 'green' : 'slate'}>{part.status.replaceAll('_', ' ')}</StatusBadge></div><div className="mt-3 text-sm text-slate-500">Last service: {part.lastService}</div></button>)}</div> : <div className="p-5"><EmptyState description="Add a part only when item-level service history is useful." title="No tracked parts" /></div>}
    </section>
    <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-card"><div className="flex items-start gap-3"><Info className="mt-0.5 h-5 w-5 shrink-0 text-blue-600" /><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-extrabold text-slate-950">Inspection activity</h2><Link className="text-sm font-extrabold text-blue-700 hover:underline" to="/maintenance/inspections">Open queue</Link></div>{inspections.length ? <div className="mt-3 space-y-2">{inspections.slice(0, 3).map((item) => <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-slate-50 p-3" key={item.id}><span className="text-sm font-semibold">{item.inspectionAreas.join(', ') || 'General vehicle condition'}</span><StatusBadge tone={item.status === 'cancelled' ? 'slate' : item.isActive ? 'amber' : 'green'}>{item.status.replaceAll('_', ' ')}</StatusBadge></div>)}</div> : <p className="mt-1 text-sm text-slate-600">No inspection activity has been recorded for this vehicle.</p>}</div></div></section>
  </div>
}

function ActivityTab({ assessments, records }: { assessments: MaintenancePrediction[]; records: MaintenanceRecord[] }) {
  const events = [
    ...assessments.map((item) => ({ id: `assessment-${item.id}`, date: item.createdAt, title: 'Risk assessment approved', detail: assessmentResult(item.risk), tone: 'blue' as const })),
    ...records.map((record) => ({ id: `service-${record.id}`, date: record.date, title: record.service, detail: `${record.status} · ${record.technician}`, tone: 'green' as const })),
  ].sort((left, right) => Date.parse(right.date) - Date.parse(left.date))
  return <section className="rounded-lg border border-slate-200 bg-white shadow-card"><div className="border-b border-slate-200 p-5"><h2 className="text-lg font-extrabold text-slate-950">Vehicle activity</h2><p className="mt-1 text-sm text-slate-500">Read-only assessment and service events in one chronology.</p></div>{events.length ? <div className="p-5">{events.map((event) => <div className="relative border-l-2 border-slate-200 pb-6 pl-6 last:pb-0" key={event.id}><span className={clsx('absolute -left-[7px] top-1 h-3 w-3 rounded-full ring-4 ring-white', event.tone === 'blue' ? 'bg-blue-600' : 'bg-emerald-600')} /><div className="text-xs font-bold text-slate-500">{assessmentDate(event.date)}</div><div className="mt-1 font-extrabold text-slate-950">{event.title}</div><div className="mt-1 text-sm text-slate-600">{event.detail}</div></div>)}</div> : <div className="p-5"><EmptyState description="Assessment and service activity will appear here." title="No activity" /></div>}</section>
}

function AssessmentMetric({ icon: Icon, label, value }: { icon: typeof Gauge; label: string; value: string }) {
  return <div className="rounded-lg border border-slate-200 bg-slate-50 p-4"><div className="flex items-center gap-2 text-xs font-bold text-slate-500"><Icon className="h-4 w-4" />{label}</div><div className="mt-2 text-lg font-extrabold text-slate-950">{value}</div></div>
}

function Summary({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0 border-b border-slate-200 p-5 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0"><div className="text-xs font-bold uppercase text-slate-500">{label}</div><div className="mt-2 text-lg font-extrabold text-slate-950">{value}</div></div>
}

const PROFILE_TONES = {
  blue: 'bg-blue-50 text-blue-700 ring-blue-100',
  emerald: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
  violet: 'bg-violet-50 text-violet-700 ring-violet-100',
  amber: 'bg-amber-50 text-amber-700 ring-amber-100',
  cyan: 'bg-cyan-50 text-cyan-700 ring-cyan-100',
  rose: 'bg-rose-50 text-rose-700 ring-rose-100',
} as const

function ProfileDetail({ icon: Icon, label, tone, value }: { icon: typeof CarFront; label: string; tone: keyof typeof PROFILE_TONES; value: string }) {
  return <div className="flex min-w-0 items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 transition-colors hover:border-slate-300 hover:bg-slate-50">
    <span className={clsx('grid h-10 w-10 shrink-0 place-items-center rounded-lg ring-1', PROFILE_TONES[tone])}><Icon aria-hidden="true" className="h-5 w-5" /></span>
    <span className="min-w-0"><span className="block text-xs font-bold uppercase text-slate-500">{label}</span><span className="mt-1 block break-words font-semibold capitalize text-slate-950">{value}</span></span>
  </div>
}
