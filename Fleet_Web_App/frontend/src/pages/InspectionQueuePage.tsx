import { ArrowRight, Search, UserRoundCheck, Wrench, XCircle } from 'lucide-react'
import { useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { InspectionAssignmentDialog } from '../components/InspectionAssignmentDialog'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from '../components/ModalLayout'
import { DataTable, EmptyState, ErrorState, LoadingState, PageHeader, SecondaryButton, StatusBadge } from '../components/UI'
import { useAsyncData } from '../hooks/useAsyncData'
import { authService } from '../services/authService'
import { fleetService } from '../services/fleetService'
import type { InspectionPriority, InspectionStatus, VehicleMaintenanceInspection } from '../types'
import { showToast } from '../utils/toast'
import { canAccess } from '../utils/permissions'

const statuses: Array<'all' | InspectionStatus> = ['all', 'pending', 'assigned', 'in_progress', 'decision_pending', 'maintenance_required', 'returned_to_service', 'cancelled']
const priorities: Array<'all' | InspectionPriority> = ['all', 'critical', 'high', 'medium', 'low']
const cancellableStatuses: InspectionStatus[] = ['pending', 'assigned', 'in_progress']

export function InspectionQueuePage() {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<'all' | InspectionStatus>('all')
  const [priority, setPriority] = useState<'all' | InspectionPriority>('all')
  const [assigning, setAssigning] = useState<VehicleMaintenanceInspection | null>(null)
  const [cancelling, setCancelling] = useState<VehicleMaintenanceInspection | null>(null)
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [inspectionPage, vehicles, assignees] = await Promise.all([
      fleetService.listInspections(),
      fleetService.listVehicles(),
      fleetService.listInspectionAssignees().catch(() => []),
    ])
    return { inspections: inspectionPage.items, vehicles, assignees }
  }, [])
  const canManage = canAccess(authService.getSession(), 'maintenance.manage')
  const rows = useMemo(() => {
    const search = query.trim().toLowerCase()
    return (data?.inspections ?? []).filter((inspection) => {
      const vehicle = data?.vehicles.find((item) => item.id === inspection.vehicleId)
      const haystack = `${vehicle?.registrationNumber ?? ''} ${vehicle?.vehicleCode ?? ''} ${vehicle?.model ?? ''}`.toLowerCase()
      return (!search || haystack.includes(search)) && (status === 'all' || inspection.status === status) && (priority === 'all' || inspection.priority === priority)
    })
  }, [data, priority, query, status])

  if (loading) return <LoadingState label="Loading inspection queue..." />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load inspection queue'} onRetry={reload} />

  const vehicleFor = (inspection: VehicleMaintenanceInspection) => data.vehicles.find((item) => item.id === inspection.vehicleId)
  const assigneeFor = (inspection: VehicleMaintenanceInspection) => data.assignees.find((item) => item.id === inspection.assignedTo)?.fullName ?? (inspection.assignedTo ? 'Assigned team member' : 'Awaiting assignment')

  return <div className="min-w-0 space-y-5">
    <PageHeader description="Assign and monitor vehicle inspections from service hold through operational decision." eyebrow={<Link className="text-sm font-bold text-blue-700 hover:underline" to="/maintenance">Maintenance Command Center</Link>} title="Inspection Queue" />
    <div className="flex min-w-0 flex-wrap gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-card">
      <label className="flex min-w-[220px] flex-1 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"><Search className="h-4 w-4 text-slate-400" /><input aria-label="Search inspection vehicles" className="min-w-0 flex-1 bg-transparent text-sm outline-none" onChange={(event) => setQuery(event.target.value)} placeholder="Registration, fleet code, or vehicle" value={query} /></label>
      <select aria-label="Inspection status" className="min-h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold capitalize" onChange={(event) => setStatus(event.target.value as typeof status)} value={status}>{statuses.map((item) => <option key={item} value={item}>{item === 'all' ? 'All statuses' : item.replaceAll('_', ' ')}</option>)}</select>
      <select aria-label="Inspection priority filter" className="min-h-10 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold capitalize" onChange={(event) => setPriority(event.target.value as typeof priority)} value={priority}>{priorities.map((item) => <option key={item} value={item}>{item === 'all' ? 'All priorities' : item}</option>)}</select>
    </div>
    {!canManage && <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm font-semibold text-blue-800">Your access is read-only. Assignment and cancellation require a maintenance manager or administrator.</div>}
    {rows.length === 0 ? <EmptyState description="Adjust the filters, or add a vehicle from its Risk Assessment workspace." title="No matching inspections" /> : <>
      <div className="hidden md:block"><DataTable headers={['Vehicle', 'Priority', 'Inspection areas', 'Assignee', 'Created', 'Status', 'Actions']}>{rows.map((inspection) => {
        const vehicle = vehicleFor(inspection)
        return <tr className="transition hover:bg-blue-50/50" key={inspection.id}><td className="px-5 py-4"><Link className="font-extrabold text-slate-950 hover:text-blue-700" to={`/vehicles/${inspection.vehicleId}?tab=parts-inspections`}>{vehicle?.registrationNumber ?? 'Unknown vehicle'}</Link><div className="text-xs text-slate-500">{vehicle?.vehicleCode ?? inspection.vehicleId}</div></td><td className="px-5 py-4"><PriorityBadge value={inspection.priority} /></td><td className="max-w-72 px-5 py-4"><div className="flex flex-wrap gap-1.5">{inspection.inspectionAreas.map((area) => <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-700" key={area}>{area}</span>)}</div></td><td className="px-5 py-4 font-semibold">{assigneeFor(inspection)}</td><td className="whitespace-nowrap px-5 py-4 text-sm font-semibold">{formatDateTime(inspection.createdAt)}</td><td className="px-5 py-4"><InspectionStatusBadge value={inspection.status} /></td><td className="px-5 py-4"><QueueActions canManage={canManage} inspection={inspection} onAssign={setAssigning} onCancel={setCancelling} /></td></tr>
      })}</DataTable></div>
      <div className="grid gap-3 md:hidden">{rows.map((inspection) => { const vehicle = vehicleFor(inspection); return <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-card" key={inspection.id}><div className="flex items-start justify-between gap-3"><div><Link className="font-extrabold text-slate-950" to={`/vehicles/${inspection.vehicleId}?tab=parts-inspections`}>{vehicle?.registrationNumber ?? 'Unknown vehicle'}</Link><div className="text-xs text-slate-500">{vehicle?.vehicleCode ?? inspection.vehicleId}</div></div><PriorityBadge value={inspection.priority} /></div><div className="mt-3 flex flex-wrap gap-1.5">{inspection.inspectionAreas.map((area) => <span className="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold" key={area}>{area}</span>)}</div><dl className="mt-4 grid grid-cols-2 gap-3 text-sm"><div><dt className="text-xs font-bold text-slate-500">Assignee</dt><dd className="mt-1 font-semibold">{assigneeFor(inspection)}</dd></div><div><dt className="text-xs font-bold text-slate-500">Status</dt><dd className="mt-1"><InspectionStatusBadge value={inspection.status} /></dd></div></dl><div className="mt-4 border-t border-slate-200 pt-3"><QueueActions canManage={canManage} inspection={inspection} onAssign={setAssigning} onCancel={setCancelling} /></div></article> })}</div>
    </>}
    {assigning && <InspectionAssignmentDialog canManage={canManage} inspection={assigning} onAssigned={async () => { showToast({ tone: 'success', title: 'Inspection assigned', message: 'The queue has been updated.' }); await reload() }} onClose={() => setAssigning(null)} />}
    {cancelling && <InspectionCancellationDialog inspection={cancelling} onCancelled={async () => { showToast({ tone: 'success', title: 'Inspection cancelled', message: 'The cancelled item remains in service history.' }); await reload() }} onClose={() => setCancelling(null)} />}
  </div>
}

function QueueActions({ inspection, canManage, onAssign, onCancel }: { inspection: VehicleMaintenanceInspection; canManage: boolean; onAssign: (value: VehicleMaintenanceInspection) => void; onCancel: (value: VehicleMaintenanceInspection) => void }) {
  return <div className="flex flex-wrap gap-2">
    {inspection.status === 'pending' && (canManage ? <button className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-blue-200 px-3 text-sm font-bold text-blue-700 transition hover:bg-blue-50" onClick={() => onAssign(inspection)} title="Assign inspection" type="button"><UserRoundCheck className="h-4 w-4" />Assign</button> : <span className="text-xs font-semibold text-slate-500">Awaiting assignment</span>)}
    {(inspection.status === 'assigned' || inspection.status === 'in_progress') && <Link className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-blue-200 px-3 text-sm font-bold text-blue-700 transition hover:bg-blue-50" to={`/maintenance/inspections/${inspection.id}`}><ArrowRight className="h-4 w-4" />Open Inspection</Link>}
    {inspection.status === 'decision_pending' && <Link className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-amber-200 px-3 text-sm font-bold text-amber-800 transition hover:bg-amber-50" to={`/maintenance/inspections/${inspection.id}/decision`}><ArrowRight className="h-4 w-4" />Review Outcome</Link>}
    {inspection.status === 'maintenance_required' && <Link className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-red-200 px-3 text-sm font-bold text-red-700 transition hover:bg-red-50" to={inspection.workOrderId ? `/maintenance/work-orders?workOrderId=${inspection.workOrderId}` : `/vehicles/${inspection.vehicleId}?tab=maintenance`}><Wrench className="h-4 w-4" />{inspection.workOrderId ? 'Linked Work' : 'Maintenance'}</Link>}
    {canManage && cancellableStatuses.includes(inspection.status) && <button aria-label="Cancel inspection" className="grid h-9 w-9 place-items-center rounded-lg border border-red-200 text-red-700 transition hover:bg-red-50" onClick={() => onCancel(inspection)} title="Cancel inspection" type="button"><XCircle className="h-4 w-4" /></button>}
  </div>
}

function InspectionCancellationDialog({ inspection, onClose, onCancelled }: { inspection: VehicleMaintenanceInspection; onClose: () => void; onCancelled: () => Promise<void> | void }) {
  const [reason, setReason] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const submit = async (event: FormEvent) => { event.preventDefault(); if (reason.trim().length < 3) { setError('Add a clear cancellation reason.'); return } setBusy(true); setError(''); try { await fleetService.cancelInspection(inspection.id, reason.trim()); await onCancelled(); onClose() } catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to cancel inspection') } finally { setBusy(false) } }
  return <ModalViewport><ModalPanel aria-modal="true" className="max-w-md" role="dialog"><form className="contents" onSubmit={submit}><ModalHeader><h2 className="text-xl font-extrabold">Cancel inspection</h2><p className="mt-1 text-sm text-slate-500">The record remains available in operational history.</p></ModalHeader><ModalBody><label className="text-sm font-bold text-slate-700">Cancellation reason<textarea autoFocus className="mt-2 min-h-28 w-full rounded-lg border border-slate-300 p-3 outline-none focus:ring-4 focus:ring-red-100" onChange={(event) => setReason(event.target.value)} required value={reason} /></label>{error && <div className="mt-3 rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-700" role="alert">{error}</div>}</ModalBody><ModalFooter><SecondaryButton onClick={onClose}>Keep inspection</SecondaryButton><button className="inline-flex min-h-10 items-center justify-center rounded-lg bg-red-600 px-4 text-sm font-bold text-white disabled:opacity-50" disabled={busy || reason.trim().length < 3} type="submit">{busy ? 'Cancelling...' : 'Cancel inspection'}</button></ModalFooter></form></ModalPanel></ModalViewport>
}

function PriorityBadge({ value }: { value: InspectionPriority }) { return <StatusBadge tone={value === 'critical' ? 'red' : value === 'high' ? 'amber' : value === 'low' ? 'green' : 'blue'}>{value}</StatusBadge> }
function InspectionStatusBadge({ value }: { value: InspectionStatus }) { return <StatusBadge tone={value === 'cancelled' ? 'slate' : value === 'returned_to_service' ? 'green' : value === 'maintenance_required' ? 'red' : value === 'in_progress' ? 'blue' : 'amber'}>{value.replaceAll('_', ' ')}</StatusBadge> }
function formatDateTime(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? 'Unknown' : date.toLocaleString() }
