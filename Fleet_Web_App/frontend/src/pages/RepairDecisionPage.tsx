import { ArrowLeft, ClipboardCheck, RotateCcw, ShieldCheck, Wrench } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from '../components/ModalLayout'
import { ErrorState, LoadingState, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { maintenancePriorityOptions, maintenanceSystemOptions } from '../features/maintenance/options'
import { useAsyncData } from '../hooks/useAsyncData'
import { authService } from '../services/authService'
import { fleetService, type InspectionDecisionPayload } from '../services/fleetService'
import type { InspectionDecision, InspectionPriority, MaintenanceSystem } from '../types'
import { showToast } from '../utils/toast'
import { canAccess } from '../utils/permissions'

export function RepairDecisionPage() {
  const { inspectionId = '' } = useParams()
  const navigate = useNavigate()
  const { data, error, loading, reload } = useAsyncData(async () => {
    const inspection = await fleetService.getInspection(inspectionId)
    const vehicle = await fleetService.getVehicle(inspection.vehicleId)
    return { inspection, vehicle }
  }, [inspectionId])
  const [decision, setDecision] = useState<InspectionDecision | null>(null)
  const canDecide = canAccess(authService.getSession(), 'maintenance.manage')

  if (loading) return <LoadingState label="Loading repair decision..." />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load repair decision'} onRetry={reload} />
  const { inspection, vehicle } = data
  const failed = inspection.checklist.filter((item) => item.outcome === 'failed')
  const duration = formatDuration(inspection.startedAt, inspection.completedAt)

  return <div className="min-w-0 space-y-5">
    <PageHeader description={`${vehicle.registrationNumber} · ${vehicle.vehicleCode} · Inspection ${inspection.status.replaceAll('_', ' ')}`} eyebrow={<Link className="inline-flex items-center gap-2 text-sm font-bold text-blue-700 hover:underline" to={`/maintenance/inspections/${inspection.id}`}><ArrowLeft className="h-4 w-4" />Inspection evidence</Link>} title="Repair Decision" />

    {inspection.status !== 'decision_pending' ? <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-card"><div className="flex items-center gap-3"><ClipboardCheck className="h-6 w-6 text-slate-500" /><div><h2 className="font-extrabold text-slate-950">Decision already recorded</h2><p className="mt-1 text-sm text-slate-600">This inspection is read-only and its operational evidence remains unchanged.</p></div></div><div className="mt-4"><StatusBadge tone={inspection.status === 'returned_to_service' ? 'green' : inspection.status === 'maintenance_required' ? 'red' : 'slate'}>{inspection.status.replaceAll('_', ' ')}</StatusBadge></div></section> : <>
      <section className="grid min-w-0 gap-4 lg:grid-cols-[minmax(0,1.3fr)_minmax(280px,.7fr)]">
        <div className="min-w-0 rounded-lg border border-slate-200 bg-white p-5 shadow-card">
          <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-lg font-extrabold text-slate-950">Inspection outcome</h2><p className="mt-1 text-sm text-slate-500">Review the immutable mechanic evidence before choosing an operational outcome.</p></div><StatusBadge tone={failed.length ? 'red' : 'green'}>{failed.length} issues found</StatusBadge></div>
          <div className="mt-5 grid gap-3 sm:grid-cols-2"><SummaryField label="Inspection duration" value={duration} /><SummaryField label="Inspection areas" value={inspection.inspectionAreas.join(', ') || 'General vehicle condition'} /></div>
          <div className="mt-5"><h3 className="text-sm font-extrabold text-slate-800">Mechanic summary</h3><p className="mt-2 whitespace-pre-wrap rounded-lg bg-slate-50 p-4 text-sm font-medium text-slate-700">{inspection.summary || 'No summary recorded'}</p></div>
        </div>
        <aside className="min-w-0 rounded-lg border border-red-200 bg-red-50 p-5"><h2 className="font-extrabold text-red-950">Issues requiring review</h2>{failed.length ? <ul className="mt-3 space-y-3">{failed.map((item) => <li className="rounded-lg bg-white p-3 shadow-sm" key={item.key}><div className="font-bold text-slate-950">{item.label}</div><p className="mt-1 text-sm text-red-800">{item.remark}</p></li>)}</ul> : <p className="mt-2 text-sm font-medium text-emerald-800">No checklist issues were recorded.</p>}</aside>
      </section>

      {canDecide ? <section className="grid gap-4 md:grid-cols-2">
        <button aria-label="Maintenance Required" className="min-h-36 rounded-lg border border-red-200 bg-white p-5 text-left shadow-card transition hover:border-red-400 hover:bg-red-50" onClick={() => setDecision('maintenance_required')} type="button"><Wrench className="h-6 w-6 text-red-700" /><div className="mt-3 text-lg font-extrabold text-slate-950">Maintenance Required</div><p className="mt-1 text-sm text-slate-600">Keep the service hold and create linked maintenance work from this inspection.</p></button>
        <button aria-label="Return to Service" className="min-h-36 rounded-lg border border-emerald-200 bg-white p-5 text-left shadow-card transition hover:border-emerald-400 hover:bg-emerald-50" onClick={() => setDecision('returned_to_service')} type="button"><ShieldCheck className="h-6 w-6 text-emerald-700" /><div className="mt-3 text-lg font-extrabold text-slate-950">Return to Service</div><p className="mt-1 text-sm text-slate-600">Release the inspection hold when evidence supports normal operation.</p></button>
      </section> : <section className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm font-semibold text-blue-800">You can review this evidence, but recording the repair decision requires a maintenance manager or administrator.</section>}
    </>}
    {decision && <DecisionDialog decision={decision} inspectionId={inspection.id} onClose={() => setDecision(null)} onSuccess={(updated) => { showToast({ tone: 'success', title: 'Decision recorded', message: decision === 'maintenance_required' ? 'Linked maintenance work has been created.' : 'The vehicle inspection hold has been released.' }); if (updated.workOrderId) navigate(`/vehicles/${updated.vehicleId}?tab=maintenance&workOrderId=${updated.workOrderId}`); else navigate('/maintenance') }} />}
  </div>
}

function DecisionDialog({ decision, inspectionId, onClose, onSuccess }: { decision: InspectionDecision; inspectionId: string; onClose: () => void; onSuccess: (inspection: Awaited<ReturnType<typeof fleetService.decideInspection>>) => void }) {
  const needsMaintenance = decision === 'maintenance_required'
  const [notes, setNotes] = useState('')
  const [maintenanceSystem, setMaintenanceSystem] = useState<MaintenanceSystem>('braking')
  const [issueType, setIssueType] = useState('')
  const [priority, setPriority] = useState<InspectionPriority>('medium')
  const [estimatedCost, setEstimatedCost] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError('')
    if (notes.trim().length < 3) { setError('Add clear decision notes.'); return }
    if (needsMaintenance && (!issueType.trim() || estimatedCost === '' || Number(estimatedCost) < 0)) { setError('Complete the maintenance system, issue type, priority, and estimated cost.'); return }
    const payload: InspectionDecisionPayload = needsMaintenance
      ? { decision, notes: notes.trim(), maintenance_system: maintenanceSystem, issue_type: issueType.trim(), priority, estimated_cost: Number(estimatedCost) }
      : { decision, notes: notes.trim() }
    setBusy(true)
    try { onSuccess(await fleetService.decideInspection(inspectionId, payload)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to record the repair decision.') }
    finally { setBusy(false) }
  }

  return <ModalViewport><ModalPanel aria-modal="true" className="max-w-2xl" role="dialog"><form className="contents" onSubmit={submit}><ModalHeader><div className="flex items-start gap-3">{needsMaintenance ? <Wrench className="mt-0.5 h-6 w-6 text-red-700" /> : <ShieldCheck className="mt-0.5 h-6 w-6 text-emerald-700" />}<div><h2 className="text-xl font-extrabold">{needsMaintenance ? 'Confirm Maintenance Required' : 'Confirm Return to Service'}</h2><p className="mt-1 text-sm text-slate-500">This operational decision is stored with the inspection evidence.</p></div></div></ModalHeader><ModalBody className="space-y-4">
    <label className="block text-sm font-bold text-slate-700">Decision notes<textarea aria-label="Decision notes" autoFocus className="mt-2 min-h-28 w-full rounded-lg border border-slate-300 p-3 font-medium outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" onChange={(event) => setNotes(event.target.value)} value={notes} /></label>
    {needsMaintenance && <div className="grid gap-4 sm:grid-cols-2">
      <label className="text-sm font-bold text-slate-700">Maintenance system<select aria-label="Maintenance system" className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3" onChange={(event) => setMaintenanceSystem(event.target.value as MaintenanceSystem)} value={maintenanceSystem}>{maintenanceSystemOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
      <label className="text-sm font-bold text-slate-700">Priority<select aria-label="Priority" className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 capitalize" onChange={(event) => setPriority(event.target.value as InspectionPriority)} value={priority}>{maintenancePriorityOptions.map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
      <label className="text-sm font-bold text-slate-700 sm:col-span-2">Issue type<input aria-label="Issue type" className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 px-3" onChange={(event) => setIssueType(event.target.value)} value={issueType} /></label>
      <label className="text-sm font-bold text-slate-700">Estimated cost (LKR)<input aria-label="Estimated cost" className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 px-3" min="0" onChange={(event) => setEstimatedCost(event.target.value)} step="0.01" type="number" value={estimatedCost} /></label>
    </div>}
    {error && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-800" role="alert">{error}</p>}
  </ModalBody><ModalFooter><SecondaryButton onClick={onClose}><RotateCcw className="h-4 w-4" />Cancel</SecondaryButton><PrimaryButton disabled={busy} type="submit">{busy ? 'Saving...' : needsMaintenance ? 'Create Maintenance Work' : 'Confirm Return to Service'}</PrimaryButton></ModalFooter></form></ModalPanel></ModalViewport>
}

function SummaryField({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border border-slate-200 p-3"><div className="text-xs font-bold uppercase text-slate-500">{label}</div><div className="mt-1 font-bold text-slate-900">{value}</div></div> }
function formatDuration(startedAt: string | null, completedAt: string | null) { if (!startedAt || !completedAt) return 'Unavailable'; const duration = Math.max(0, new Date(completedAt).getTime() - new Date(startedAt).getTime()); if (!Number.isFinite(duration)) return 'Unavailable'; const minutes = Math.round(duration / 60000); return `${Math.floor(minutes / 60)} hr ${minutes % 60} min` }
