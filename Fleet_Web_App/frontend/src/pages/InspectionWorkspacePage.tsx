import { ArrowLeft, CheckCircle2, Clock3, FileCheck2, Play, Save, ShieldAlert } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { InspectionChecklist } from '../components/InspectionChecklist'
import { validateInspectionChecklist, type InspectionChecklistFormItem } from '../features/maintenance/inspectionChecklist'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from '../components/ModalLayout'
import { ErrorState, LoadingState, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { useAsyncData } from '../hooks/useAsyncData'
import { authService } from '../services/authService'
import { canAccess } from '../utils/permissions'
import { fleetService } from '../services/fleetService'
import type { InspectionChecklistItem, VehicleMaintenanceInspection } from '../types'
import { showToast } from '../utils/toast'

const readOnlyStatuses = new Set(['completed', 'decision_pending', 'maintenance_required', 'maintenance_completed', 'returned_to_service', 'cancelled'])

export function InspectionWorkspacePage() {
  const { inspectionId = '' } = useParams()
  const navigate = useNavigate()
  const { data, error, loading, reload, setData } = useAsyncData(async () => {
    const inspection = await fleetService.getInspection(inspectionId)
    const vehicle = await fleetService.getVehicle(inspection.vehicleId)
    return { inspection, vehicle }
  }, [inspectionId])
  const [items, setItems] = useState<InspectionChecklistFormItem[]>([])
  const [summary, setSummary] = useState('')
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})
  const [operationError, setOperationError] = useState('')
  const [saving, setSaving] = useState(false)
  const [savedAt, setSavedAt] = useState<string | null>(null)
  const [startOpen, setStartOpen] = useState(false)
  const [completeOpen, setCompleteOpen] = useState(false)
  const currentUser = authService.getSession()

  useEffect(() => {
    if (!data) return
    const { inspection } = data
    const terminal = readOnlyStatuses.has(inspection.status)
    const source = terminal ? inspection.checklist : inspection.draftChecklist
    const byKey = new Map(source.map((item) => [item.key, item]))
    const areas = inspection.inspectionAreas.length ? inspection.inspectionAreas : ['General vehicle condition']
    const next = areas.map((area, index) => {
      const key = areaKey(area, index)
      const saved = byKey.get(key) ?? source.find((item) => item.label === area)
      return { key, label: area, outcome: saved?.outcome ?? null, remark: saved?.remark ?? '' }
    })
    for (const saved of source) {
      if (!next.some((item) => item.key === saved.key)) next.push({ key: saved.key, label: saved.label, outcome: saved.outcome, remark: saved.remark ?? '' })
    }
    let active = true
    queueMicrotask(() => {
      if (!active) return
      setItems(next)
      setSummary((terminal ? inspection.summary : inspection.draftSummary) ?? '')
      setSavedAt(inspection.draftSavedAt)
    })
    return () => { active = false }
  }, [data])

  const elapsed = useElapsed(data?.inspection.startedAt ?? null, data?.inspection.completedAt ?? null)
  const terminal = data ? readOnlyStatuses.has(data.inspection.status) : true
  const canExecute = Boolean(
    data
      && currentUser
      && canAccess(currentUser, 'maintenance.manage')
      && data.inspection.assignedTo === currentUser.id,
  )
  const interactive = Boolean(data?.inspection.status === 'in_progress' && canExecute)

  const saveDraft = async () => {
    const errors = validateInspectionChecklist(items, false)
    setValidationErrors(errors)
    if (Object.keys(errors).length) return
    setSaving(true); setOperationError('')
    try {
      const updated = await fleetService.saveInspectionDraft(inspectionId, {
        checklist: toPayload(items.filter((item) => item.outcome !== null)),
        summary: summary.trim() || null,
      })
      setSavedAt(updated.draftSavedAt)
      setData((current) => current ? { ...current, inspection: updated } : current)
      showToast({ tone: 'success', title: 'Draft saved', message: 'Inspection evidence is stored securely.' })
    } catch (cause) {
      setOperationError(errorMessage(cause, 'Unable to save the inspection draft.'))
    } finally { setSaving(false) }
  }

  const requestCompletion = () => {
    const errors = validateInspectionChecklist(items, true)
    if (!summary.trim()) errors.summary = 'Add a complete inspection summary.'
    setValidationErrors(errors)
    if (Object.keys(errors).length) return
    setCompleteOpen(true)
  }

  if (loading) return <LoadingState label="Loading inspection workspace..." />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load inspection workspace'} onRetry={reload} />
  const { inspection, vehicle } = data

  return <div className="min-w-0 space-y-5">
    <PageHeader
      action={inspection.status === 'assigned' && canExecute ? <PrimaryButton onClick={() => setStartOpen(true)}><Play className="h-4 w-4" />Start Inspection</PrimaryButton> : inspection.status === 'decision_pending' ? <PrimaryButton onClick={() => navigate(`/maintenance/inspections/${inspection.id}/decision`)}><ShieldAlert className="h-4 w-4" />Repair Decision</PrimaryButton> : undefined}
      description={`${vehicle.registrationNumber} · ${vehicle.vehicleCode} · ${vehicle.model}`}
      eyebrow={<Link className="inline-flex items-center gap-2 text-sm font-bold text-blue-700 hover:underline" to="/maintenance/inspections"><ArrowLeft className="h-4 w-4" />Inspection Queue</Link>}
      title="Mechanic Inspection Workspace"
    />

    <section className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <InfoCard label="Status" value={<StatusBadge tone={statusTone(inspection.status)}>{inspection.status.replaceAll('_', ' ')}</StatusBadge>} />
      <InfoCard label="Priority" value={<span className="capitalize">{inspection.priority}</span>} />
      <InfoCard label="Elapsed time" value={<span className="font-mono">{elapsed}</span>} icon={Clock3} />
      <InfoCard label="Evidence" value={terminal ? 'Final record' : savedAt ? `Saved ${formatDateTime(savedAt)}` : 'Not saved yet'} icon={FileCheck2} />
    </section>

    {inspection.status === 'assigned' && <section className="rounded-lg border border-blue-200 bg-blue-50 p-5"><h2 className="font-extrabold text-blue-950">{canExecute ? 'Ready to begin' : 'Assigned inspection'}</h2><p className="mt-1 text-sm font-medium text-blue-800">{canExecute ? 'Start the inspection to activate elapsed-time tracking and the structured checklist.' : 'Only the assigned maintenance team member can start this inspection.'}</p></section>}

    {(inspection.status === 'in_progress' || terminal) && <>
      <section>
        <div className="mb-3"><h2 className="text-lg font-extrabold text-slate-950">Inspection checklist</h2><p className="mt-1 text-sm text-slate-500">Record one controlled outcome for each assigned inspection area.</p></div>
        <InspectionChecklist errors={validationErrors} items={items} onChange={setItems} readOnly={!interactive} />
      </section>
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-card">
        <label className="block text-sm font-bold text-slate-700">Inspection summary
          {!interactive ? <p className="mt-2 min-h-20 whitespace-pre-wrap rounded-lg bg-slate-50 p-4 font-medium text-slate-800">{summary || 'No summary recorded'}</p> : <textarea aria-label="Inspection summary" className="mt-2 min-h-32 w-full rounded-lg border border-slate-300 p-3 font-medium outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" onChange={(event) => setSummary(event.target.value)} placeholder="Summarize the overall condition, checks performed, and next recommendation." value={summary} />}
        </label>
        {validationErrors.summary && <p className="mt-2 text-sm font-semibold text-red-700" role="alert">{validationErrors.summary}</p>}
      </section>
    </>}

    {operationError && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800" role="alert">{operationError}</div>}
    {interactive && <div className="sticky bottom-3 z-[5] flex flex-col gap-2 rounded-xl border border-slate-200 bg-white/95 p-3 pb-[max(.75rem,env(safe-area-inset-bottom))] shadow-xl backdrop-blur sm:flex-row sm:justify-end">
      <SecondaryButton disabled={saving} onClick={saveDraft}><Save className="h-4 w-4" />{saving ? 'Saving...' : 'Save draft'}</SecondaryButton>
      <PrimaryButton disabled={saving} onClick={requestCompletion}><CheckCircle2 className="h-4 w-4" />End Inspection</PrimaryButton>
    </div>}

    {startOpen && <StartInspectionDialog inspectionId={inspection.id} onClose={() => setStartOpen(false)} onStarted={(updated) => { setData({ inspection: updated, vehicle }); setStartOpen(false) }} />}
    {completeOpen && <CompleteInspectionDialog inspectionId={inspection.id} items={items} summary={summary.trim()} onClose={() => setCompleteOpen(false)} onCompleted={(updated) => { setData({ inspection: updated, vehicle }); setCompleteOpen(false); navigate(`/maintenance/inspections/${inspection.id}/decision`) }} />}
  </div>
}

function StartInspectionDialog({ inspectionId, onClose, onStarted }: { inspectionId: string; onClose: () => void; onStarted: (inspection: VehicleMaintenanceInspection) => void }) {
  const [notes, setNotes] = useState(''); const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const submit = async (event: FormEvent) => { event.preventDefault(); setBusy(true); setError(''); try { onStarted(await fleetService.startInspection(inspectionId, notes.trim() ? { notes: notes.trim() } : {})) } catch (cause) { setError(errorMessage(cause, 'Unable to start this inspection.')) } finally { setBusy(false) } }
  return <ModalViewport><ModalPanel aria-modal="true" className="max-w-lg" role="dialog"><form className="contents" onSubmit={submit}><ModalHeader><h2 className="text-xl font-extrabold">Start inspection</h2><p className="mt-1 text-sm text-slate-500">Elapsed time begins when the server accepts this action.</p></ModalHeader><ModalBody><label className="text-sm font-bold text-slate-700">Opening note (optional)<textarea className="mt-2 min-h-24 w-full rounded-lg border border-slate-300 p-3" onChange={(event) => setNotes(event.target.value)} value={notes} /></label>{error && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-700" role="alert">{error}</p>}</ModalBody><ModalFooter><SecondaryButton onClick={onClose}>Cancel</SecondaryButton><PrimaryButton disabled={busy} type="submit">{busy ? 'Starting...' : 'Start Inspection'}</PrimaryButton></ModalFooter></form></ModalPanel></ModalViewport>
}

function CompleteInspectionDialog({ inspectionId, items, summary, onClose, onCompleted }: { inspectionId: string; items: InspectionChecklistFormItem[]; summary: string; onClose: () => void; onCompleted: (inspection: VehicleMaintenanceInspection) => void }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState('')
  const complete = async () => { setBusy(true); setError(''); try { onCompleted(await fleetService.completeInspection(inspectionId, { checklist: toPayload(items), summary })) } catch (cause) { setError(errorMessage(cause, 'Unable to complete this inspection.')) } finally { setBusy(false) } }
  return <ModalViewport><ModalPanel aria-modal="true" className="max-w-lg" role="dialog"><ModalHeader><h2 className="text-xl font-extrabold">End inspection?</h2><p className="mt-1 text-sm text-slate-500">The checklist becomes immutable and moves to repair decision.</p></ModalHeader><ModalBody><p className="text-sm font-medium text-slate-700">Confirm that all evidence and the final summary are complete.</p>{error && <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-700" role="alert">{error}</p>}</ModalBody><ModalFooter><SecondaryButton onClick={onClose}>Continue inspection</SecondaryButton><PrimaryButton disabled={busy} onClick={complete}>{busy ? 'Ending...' : 'End Inspection'}</PrimaryButton></ModalFooter></ModalPanel></ModalViewport>
}

function toPayload(items: InspectionChecklistFormItem[]): InspectionChecklistItem[] { return items.filter((item): item is InspectionChecklistFormItem & { outcome: NonNullable<InspectionChecklistFormItem['outcome']> } => item.outcome !== null).map((item) => ({ key: item.key, label: item.label, outcome: item.outcome, remark: item.remark.trim() || null })) }
function areaKey(area: string, index: number) { return area.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '') || `inspection_area_${index + 1}` }
function errorMessage(cause: unknown, fallback: string) { return cause instanceof Error ? cause.message : fallback }
function formatDateTime(value: string | null) { if (!value) return 'Unknown'; const date = new Date(value); return Number.isNaN(date.getTime()) ? 'Unknown' : date.toLocaleString() }
function statusTone(status: VehicleMaintenanceInspection['status']): 'green' | 'red' | 'blue' | 'amber' | 'slate' { return status === 'returned_to_service' || status === 'maintenance_completed' ? 'green' : status === 'maintenance_required' || status === 'cancelled' ? 'red' : status === 'in_progress' ? 'blue' : status === 'decision_pending' ? 'amber' : 'slate' }

function useElapsed(startedAt: string | null, completedAt: string | null) {
  const [now, setNow] = useState<number | null>(completedAt ? new Date(completedAt).getTime() : null)
  useEffect(() => {
    if (!startedAt || completedAt) return
    let active = true
    const update = () => { if (active) setNow(Date.now()) }
    queueMicrotask(update)
    const timer = window.setInterval(update, 1000)
    return () => { active = false; window.clearInterval(timer) }
  }, [completedAt, startedAt])
  return useMemo(() => {
    if (!startedAt) return 'Not started'
    const start = new Date(startedAt).getTime(); const end = completedAt ? new Date(completedAt).getTime() : now
    if (end === null) return 'Starting...'
    if (!Number.isFinite(start) || !Number.isFinite(end)) return 'Unavailable'
    const seconds = Math.max(0, Math.floor((end - start) / 1000)); const hours = Math.floor(seconds / 3600); const minutes = Math.floor((seconds % 3600) / 60)
    return [hours, minutes, seconds % 60].map((value) => String(value).padStart(2, '0')).join(':')
  }, [completedAt, now, startedAt])
}

function InfoCard({ label, value, icon: Icon }: { label: string; value: React.ReactNode; icon?: typeof Clock3 }) { return <div className="min-w-0 rounded-lg border border-slate-200 bg-white p-4 shadow-card"><div className="flex items-center gap-2 text-xs font-bold uppercase text-slate-500">{Icon && <Icon className="h-4 w-4" />}{label}</div><div className="mt-2 min-w-0 font-extrabold text-slate-950">{value}</div></div> }
