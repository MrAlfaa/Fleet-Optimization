import { CheckCircle2, ClipboardCheck, Play, Search, X } from 'lucide-react'
import { useMemo, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from '../components/ModalLayout'
import { DataTable, EmptyState, ErrorState, LoadingState, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { useAsyncData } from '../hooks/useAsyncData'
import { fleetService } from '../services/fleetService'
import { authService } from '../services/authService'
import { canAccess } from '../utils/permissions'
import type { MaintenanceRecord, MaintenanceWorkOrderStatus, Vehicle } from '../types'

const ACTIVE_STATUSES: MaintenanceWorkOrderStatus[] = ['planned', 'approved', 'in_progress']
const ALL_STATUSES: Array<'active' | MaintenanceWorkOrderStatus> = ['active', 'planned', 'approved', 'in_progress', 'completed', 'cancelled']

export function MaintenanceWorkOrdersPage() {
  const [params, setParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<'active' | MaintenanceWorkOrderStatus>('active')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [dialog, setDialog] = useState<'complete' | 'cancel' | null>(null)
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const { data, loading, error, reload } = useAsyncData(async () => {
    const [records, vehicles] = await Promise.all([fleetService.listMaintenanceRecords({ limit: 100 }), fleetService.listVehicles()])
    return { records: records.filter((record) => record.workOrderStatus), vehicles }
  })
  const canManage = canAccess(authService.getSession(), 'maintenance.manage')
  const requestedId = params.get('workOrderId')
  const selected = data?.records.find((record) => record.id === (selectedId ?? requestedId)) ?? null

  const visible = useMemo(() => {
    if (!data) return []
    const term = search.trim().toLowerCase()
    return data.records.filter((record) => {
      const vehicle = data.vehicles.find((item) => item.id === record.vehicleId)
      const matchesStatus = status === 'active' ? Boolean(record.workOrderStatus && ACTIVE_STATUSES.includes(record.workOrderStatus)) : record.workOrderStatus === status
      const haystack = `${vehicle?.registrationNumber ?? record.vehicle} ${vehicle?.vehicleCode ?? ''} ${record.maintenanceSystem ?? ''} ${record.issueType}`.toLowerCase()
      return matchesStatus && (!term || haystack.includes(term))
    })
  }, [data, search, status])

  const clearSelection = () => {
    setSelectedId(null)
    setDialog(null)
    setActionError('')
    if (!requestedId) return
    const next = new URLSearchParams(params)
    next.delete('workOrderId')
    setParams(next, { replace: true })
  }

  const perform = async (action: 'approve' | 'start') => {
    if (!selected) return
    setBusy(true); setActionError('')
    try {
      const updated = action === 'approve' ? await fleetService.approveMaintenance(selected.id) : await fleetService.startMaintenance(selected.id)
      setSelectedId(updated.id); setNotice(action === 'approve' ? 'Work order approved.' : 'Work started.'); await reload()
    } catch (reason) { setActionError(reason instanceof Error ? reason.message : 'Unable to update work order') }
    finally { setBusy(false) }
  }

  const submitComplete = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!selected) return
    const form = new FormData(event.currentTarget)
    const actualCost = Number(form.get('actual_cost'))
    const evidence = String(form.get('completion_evidence') ?? '').trim()
    if (!Number.isFinite(actualCost) || actualCost < 0 || evidence.length < 3) { setActionError('Enter a valid actual cost and detailed completion evidence.'); return }
    setBusy(true); setActionError('')
    try {
      const updated = await fleetService.completeMaintenance(selected.id, { actual_cost: actualCost, completion_evidence: evidence, notes: text(form, 'notes'), technician_name: text(form, 'technician_name'), service_center: text(form, 'service_center') })
      setSelectedId(updated.id); setDialog(null); setNotice('Work order completed and vehicle readiness refreshed.'); await reload()
    } catch (reason) { setActionError(reason instanceof Error ? reason.message : 'Unable to complete work order') }
    finally { setBusy(false) }
  }

  const submitCancel = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!selected) return
    const reason = String(new FormData(event.currentTarget).get('reason') ?? '').trim()
    if (reason.length < 3) { setActionError('Enter a cancellation reason.'); return }
    setBusy(true); setActionError('')
    try { const updated = await fleetService.cancelMaintenance(selected.id, reason); setSelectedId(updated.id); setDialog(null); setNotice('Work order cancelled.'); await reload() }
    catch (cause) { setActionError(cause instanceof Error ? cause.message : 'Unable to cancel work order') }
    finally { setBusy(false) }
  }

  if (loading) return <LoadingState label="Loading maintenance work orders..." />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load work orders'} onRetry={reload} />
  const vehicleFor = (id: string) => data.vehicles.find((item) => item.id === id)

  return <div className="min-w-0 space-y-5">
    <PageHeader eyebrow={<Link className="text-sm font-bold text-blue-700 hover:underline" to="/maintenance">Maintenance Command Center</Link>} title="Maintenance Work Orders" description="Approve, start, and close explicitly selected vehicle service work." />
    {notice && <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm font-bold text-emerald-800" role="status">{notice}</div>}
    {!canManage && <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm font-semibold text-blue-800">Your access is read-only. Work-order actions require a maintenance manager or administrator.</div>}
    <section className="flex min-w-0 flex-wrap gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-card">
      <label className="flex min-w-[220px] flex-1 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3"><Search className="h-4 w-4 text-slate-400" /><input aria-label="Search work orders" className="min-h-11 min-w-0 flex-1 bg-transparent outline-none" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Registration, fleet code, system or issue" /></label>
      <label className="text-sm font-bold text-slate-600"><span className="sr-only">Work order status</span><select aria-label="Work order status" className="min-h-11 rounded-lg border border-slate-200 px-3" value={status} onChange={(event) => setStatus(event.target.value as typeof status)}>{ALL_STATUSES.map((item) => <option key={item} value={item}>{label(item)}</option>)}</select></label>
    </section>
    {visible.length === 0 ? <EmptyState title="No matching work orders" description="Adjust the search or lifecycle filter." /> : <>
      <div className="hidden md:block"><DataTable headers={['Vehicle', 'Service work', 'Priority', 'Estimate / actual', 'Status', 'Created / scheduled', 'Action']}>{visible.map((record) => <WorkOrderRow key={record.id} record={record} vehicle={vehicleFor(record.vehicleId)} onOpen={() => { setSelectedId(record.id); setActionError('') }} />)}</DataTable></div>
      <div className="grid gap-3 md:hidden">{visible.map((record) => <WorkOrderCard key={record.id} record={record} vehicle={vehicleFor(record.vehicleId)} onOpen={() => { setSelectedId(record.id); setActionError('') }} />)}</div>
    </>}
    {selected && !dialog && <WorkOrderDetail canManage={canManage} error={actionError} busy={busy} record={selected} vehicle={vehicleFor(selected.vehicleId)} onClose={clearSelection} onApprove={() => perform('approve')} onStart={() => perform('start')} onComplete={() => { setDialog('complete'); setActionError('') }} onCancel={() => { setDialog('cancel'); setActionError('') }} />}
    {selected && dialog === 'complete' && <CompleteDialog busy={busy} error={actionError} onClose={() => setDialog(null)} onSubmit={submitComplete} />}
    {selected && dialog === 'cancel' && <CancelDialog busy={busy} error={actionError} onClose={() => setDialog(null)} onSubmit={submitCancel} />}
  </div>
}

function WorkOrderRow({ record, vehicle, onOpen }: { record: MaintenanceRecord; vehicle?: Vehicle; onOpen: () => void }) { return <tr className="cursor-pointer transition hover:bg-blue-50/50" onClick={onOpen}><td className="px-5 py-4"><strong>{vehicle?.registrationNumber ?? record.vehicle}</strong><div className="text-xs text-slate-500">{vehicle?.vehicleCode ?? record.vehicleId}</div></td><td className="px-5 py-4"><strong>{systemLabel(record.maintenanceSystem)}</strong><div className="max-w-72 text-xs text-slate-500">{record.issueType}</div></td><td className="px-5 py-4 capitalize">{record.priority}</td><td className="px-5 py-4">{money(record.estimatedCost)} / {money(record.actualCost)}</td><td className="px-5 py-4"><WorkStatus value={record.workOrderStatus} /></td><td className="px-5 py-4"><div>{dateTime(record.createdAt)}</div><div className="text-xs text-slate-500">{record.serviceDate ? dateTime(record.serviceDate) : 'Not scheduled'}</div></td><td className="px-5 py-4"><button className="rounded-md px-3 py-2 font-bold text-blue-700 hover:bg-blue-50" onClick={(event) => { event.stopPropagation(); onOpen() }} type="button">Open</button></td></tr> }
function WorkOrderCard({ record, vehicle, onOpen }: { record: MaintenanceRecord; vehicle?: Vehicle; onOpen: () => void }) { return <button className="rounded-lg border border-slate-200 bg-white p-4 text-left shadow-card transition hover:border-blue-300" onClick={onOpen} type="button"><div className="flex items-start justify-between gap-3"><div><div className="font-extrabold">{vehicle?.registrationNumber ?? record.vehicle}</div><div className="text-xs text-slate-500">{vehicle?.vehicleCode}</div></div><WorkStatus value={record.workOrderStatus} /></div><div className="mt-4 font-bold">{systemLabel(record.maintenanceSystem)}</div><div className="mt-1 text-sm text-slate-600">{record.issueType}</div><div className="mt-4 flex justify-between text-sm"><span className="capitalize">{record.priority} priority</span><span>{money(record.estimatedCost)}</span></div></button> }

function WorkOrderDetail({ record, vehicle, canManage, busy, error, onClose, onApprove, onStart, onComplete, onCancel }: { record: MaintenanceRecord; vehicle?: Vehicle; canManage: boolean; busy: boolean; error: string; onClose: () => void; onApprove: () => void; onStart: () => void; onComplete: () => void; onCancel: () => void }) {
  const active = Boolean(record.workOrderStatus && ACTIVE_STATUSES.includes(record.workOrderStatus))
  return <ModalViewport align="right"><ModalPanel className="max-w-xl" role="dialog" aria-modal="true"><ModalHeader className="flex items-start justify-between gap-3"><div><div className="text-xs font-bold uppercase text-slate-500">Work order</div><h2 className="mt-1 text-xl font-extrabold">{vehicle?.registrationNumber ?? record.vehicle}</h2><p className="mt-1 text-sm text-slate-500">{systemLabel(record.maintenanceSystem)} · {record.issueType}</p></div><button aria-label="Close work order" onClick={onClose} type="button"><X /></button></ModalHeader><ModalBody className="space-y-5"><div className="grid grid-cols-2 gap-4"><Detail label="Status" value={label(record.workOrderStatus ?? record.status)} /><Detail label="Priority" value={record.priority} /><Detail label="Estimated cost" value={money(record.estimatedCost)} /><Detail label="Actual cost" value={money(record.actualCost)} /><Detail label="Scheduled" value={record.serviceDate ? dateTime(record.serviceDate) : 'Not scheduled'} /><Detail label="Started" value={dateTime(record.startedAt)} /></div>{record.completionEvidence && <section className="rounded-lg bg-emerald-50 p-4"><h3 className="font-bold text-emerald-900">Completion evidence</h3><p className="mt-2 whitespace-pre-wrap text-sm text-emerald-800">{record.completionEvidence}</p></section>}{record.cancellationReason && <section className="rounded-lg bg-slate-100 p-4"><h3 className="font-bold">Cancellation reason</h3><p className="mt-2 text-sm">{record.cancellationReason}</p></section>}{error && <p className="rounded-lg bg-red-50 p-3 text-sm font-bold text-red-700">{error}</p>}</ModalBody><ModalFooter><SecondaryButton onClick={onClose}>Close</SecondaryButton>{canManage && active && <SecondaryButton disabled={busy} onClick={onCancel}>Cancel Work</SecondaryButton>}{canManage && record.workOrderStatus === 'planned' && <PrimaryButton disabled={busy} onClick={onApprove}><ClipboardCheck className="h-4 w-4" />Approve</PrimaryButton>}{canManage && record.workOrderStatus === 'approved' && <PrimaryButton disabled={busy} onClick={onStart}><Play className="h-4 w-4" />Start Work</PrimaryButton>}{canManage && record.workOrderStatus === 'in_progress' && <PrimaryButton disabled={busy} onClick={onComplete}><CheckCircle2 className="h-4 w-4" />Complete Work</PrimaryButton>}</ModalFooter></ModalPanel></ModalViewport>
}

function CompleteDialog({ busy, error, onClose, onSubmit }: { busy: boolean; error: string; onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) { return <ModalViewport><ModalPanel className="max-w-lg" role="dialog" aria-modal="true"><form className="contents" onSubmit={onSubmit}><ModalHeader><h2 className="text-xl font-extrabold">Complete Work Order</h2><p className="mt-1 text-sm text-slate-500">Record final cost and verifiable service work.</p></ModalHeader><ModalBody className="space-y-4"><Field label="Actual cost" name="actual_cost" type="number" min="0" step="0.01" /><label className="block text-sm font-bold text-slate-600">Completion evidence<textarea aria-label="Completion evidence" className="mt-2 min-h-32 w-full rounded-lg border border-slate-200 p-3" minLength={3} name="completion_evidence" required /></label><Field label="Technician" name="technician_name" required={false} /><Field label="Service center" name="service_center" required={false} /><label className="block text-sm font-bold text-slate-600">Notes<textarea className="mt-2 min-h-20 w-full rounded-lg border border-slate-200 p-3" name="notes" /></label>{error && <p className="rounded-lg bg-red-50 p-3 text-sm font-bold text-red-700">{error}</p>}</ModalBody><ModalFooter><SecondaryButton onClick={onClose}>Back</SecondaryButton><PrimaryButton disabled={busy} type="submit">{busy ? 'Completing...' : 'Complete Work'}</PrimaryButton></ModalFooter></form></ModalPanel></ModalViewport> }
function CancelDialog({ busy, error, onClose, onSubmit }: { busy: boolean; error: string; onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void }) { return <ModalViewport><ModalPanel className="max-w-md" role="dialog" aria-modal="true"><form className="contents" onSubmit={onSubmit}><ModalHeader><h2 className="text-xl font-extrabold">Cancel Work Order</h2></ModalHeader><ModalBody><label className="block text-sm font-bold text-slate-600">Reason<textarea aria-label="Cancellation reason" className="mt-2 min-h-28 w-full rounded-lg border border-slate-200 p-3" minLength={3} name="reason" required /></label>{error && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm font-bold text-red-700">{error}</p>}</ModalBody><ModalFooter><SecondaryButton onClick={onClose}>Back</SecondaryButton><PrimaryButton disabled={busy} type="submit">{busy ? 'Cancelling...' : 'Confirm Cancellation'}</PrimaryButton></ModalFooter></form></ModalPanel></ModalViewport> }
function Field({ label: textLabel, name, type = 'text', required = true, ...rest }: { label: string; name: string; type?: string; required?: boolean; min?: string; step?: string }) { return <label className="block text-sm font-bold text-slate-600">{textLabel}<input aria-label={textLabel} className="mt-2 min-h-11 w-full rounded-lg border border-slate-200 px-3" name={name} required={required} type={type} {...rest} /></label> }
function WorkStatus({ value }: { value: MaintenanceRecord['workOrderStatus'] }) { const tone = value === 'completed' ? 'green' : value === 'cancelled' ? 'slate' : value === 'in_progress' ? 'blue' : 'amber'; return <StatusBadge tone={tone}>{label(value ?? 'legacy')}</StatusBadge> }
function Detail({ label: textLabel, value }: { label: string; value: string }) { return <div><div className="text-xs font-bold uppercase text-slate-500">{textLabel}</div><div className="mt-1 font-semibold capitalize">{value}</div></div> }
function text(form: FormData, key: string) { const value = String(form.get(key) ?? '').trim(); return value || undefined }
function label(value: string) { return value.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase()) }
function systemLabel(value?: string) { return label(value || 'General service') }
function money(value: number | null | undefined) { return value === null || value === undefined ? 'Not recorded' : `LKR ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` }
function dateTime(value: string | null | undefined) { if (!value) return 'Not recorded'; const parsed = new Date(value); return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString() }
