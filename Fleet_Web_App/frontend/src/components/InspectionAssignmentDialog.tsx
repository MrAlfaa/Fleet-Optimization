import { UserRoundCheck, X } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { fleetService } from '../services/fleetService'
import type { InspectionAssignee, VehicleMaintenanceInspection } from '../types'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from './ModalLayout'
import { PrimaryButton, SecondaryButton } from './UI'

export function InspectionAssignmentDialog({ inspection, canManage, onClose, onAssigned }: {
  inspection: VehicleMaintenanceInspection
  canManage: boolean
  onClose: () => void
  onAssigned: () => Promise<void> | void
}) {
  const [assignees, setAssignees] = useState<InspectionAssignee[]>([])
  const [assignedTo, setAssignedTo] = useState('')
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(canManage)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!canManage) return
    fleetService.listInspectionAssignees()
      .then((items) => { setAssignees(items); setAssignedTo(items[0]?.id ?? '') })
      .catch((reason) => setError(reason instanceof Error ? reason.message : 'Unable to load the maintenance team'))
      .finally(() => setLoading(false))
  }, [canManage])

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!canManage || !assignedTo) return
    setBusy(true); setError('')
    try {
      await fleetService.assignInspection(inspection.id, { assigned_to: assignedTo, ...(notes.trim() ? { notes: notes.trim() } : {}) })
      await onAssigned()
      onClose()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to assign this inspection')
    } finally { setBusy(false) }
  }

  return <ModalViewport><ModalPanel aria-modal="true" className="max-w-lg" role="dialog"><form className="contents" onSubmit={submit}>
    <ModalHeader className="flex items-start justify-between gap-4"><div><div className="flex items-center gap-2"><UserRoundCheck className="h-5 w-5 text-blue-600" /><h2 className="text-xl font-extrabold">Assign inspection</h2></div><p className="mt-1 text-sm text-slate-500">Select an accountable maintenance team member.</p></div><button aria-label="Close assignment dialog" className="rounded-lg p-2 hover:bg-slate-100" onClick={onClose} title="Close" type="button"><X className="h-5 w-5" /></button></ModalHeader>
    <ModalBody className="space-y-4">
      {!canManage ? <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-800" role="alert">You can view this inspection, but assignment requires a maintenance manager or administrator.</div> : <>
        <label className="block text-sm font-bold text-slate-700">Assigned team member<select aria-label="Assigned team member" className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" disabled={loading || busy} onChange={(event) => setAssignedTo(event.target.value)} required value={assignedTo}><option value="">{loading ? 'Loading team...' : 'Select team member'}</option>{assignees.map((item) => <option key={item.id} value={item.id}>{item.fullName} · {item.role === 'admin' ? 'Administrator' : 'Maintenance Manager'}</option>)}</select></label>
        <label className="block text-sm font-bold text-slate-700">Assignment note <span className="font-medium text-slate-400">(optional)</span><textarea className="mt-2 min-h-24 w-full resize-y rounded-lg border border-slate-300 p-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" onChange={(event) => setNotes(event.target.value)} placeholder="Add timing or access instructions" value={notes} /></label>
        {!loading && assignees.length === 0 && !error && <div className="rounded-lg bg-slate-50 p-4 text-sm font-semibold text-slate-600">No active maintenance team members are available.</div>}
      </>}
      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700" role="alert">{error}</div>}
    </ModalBody>
    <ModalFooter><SecondaryButton onClick={onClose}>Cancel</SecondaryButton>{canManage && <PrimaryButton disabled={busy || loading || !assignedTo} type="submit">{busy ? 'Assigning...' : 'Assign inspection'}</PrimaryButton>}</ModalFooter>
  </form></ModalPanel></ModalViewport>
}
