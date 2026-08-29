import { ClipboardPlus, X } from 'lucide-react'
import { useMemo, useState, type FormEvent } from 'react'
import { fleetService } from '../services/fleetService'
import type { InspectionPriority, MaintenancePrediction, Vehicle } from '../types'
import { showToast } from '../utils/toast'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from './ModalLayout'
import { PrimaryButton, SecondaryButton } from './UI'

export function AddInspectionDialog({ vehicle, assessment, onClose, onCreated }: {
  vehicle: Vehicle
  assessment: MaintenancePrediction
  onClose: () => void
  onCreated: () => Promise<void> | void
}) {
  const suggestedAreas = useMemo(() => assessment.systemRisks.slice(0, 3).map((item) => item.name), [assessment])
  const [areas, setAreas] = useState<string[]>(suggestedAreas.length ? suggestedAreas : ['General vehicle condition'])
  const [priority, setPriority] = useState<InspectionPriority>(assessment.risk === 'critical' ? 'critical' : assessment.risk === 'high' ? 'high' : 'medium')
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (!areas.length) { setError('Select at least one inspection area.'); return }
    setBusy(true); setError('')
    try {
      await fleetService.createInspection({
        vehicle_id: vehicle.id,
        assessment_id: assessment.id,
        feature_hash: assessment.featureHash,
        priority,
        inspection_areas: areas,
        ...(notes.trim() ? { notes: notes.trim() } : {}),
      })
      showToast({ tone: 'success', title: 'Inspection added', message: `${vehicle.registrationNumber} is now in the inspection queue.` })
      await onCreated()
      onClose()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to add this vehicle to inspection')
    } finally { setBusy(false) }
  }

  return <ModalViewport><ModalPanel aria-modal="true" className="max-w-xl" role="dialog"><form className="contents" onSubmit={submit}>
    <ModalHeader className="flex items-start justify-between gap-4"><div><div className="flex items-center gap-2"><ClipboardPlus className="h-5 w-5 text-blue-600" /><h2 className="text-xl font-extrabold">Add to inspection</h2></div><p className="mt-1 text-sm text-slate-500">{vehicle.registrationNumber} · Confirm the operational scope before placing the service hold.</p></div><button aria-label="Close add inspection dialog" className="rounded-lg p-2 hover:bg-slate-100" onClick={onClose} title="Close" type="button"><X className="h-5 w-5" /></button></ModalHeader>
    <ModalBody className="space-y-5">
      <label className="block text-sm font-bold text-slate-700">Priority<select aria-label="Inspection priority" className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 capitalize outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" onChange={(event) => setPriority(event.target.value as InspectionPriority)} value={priority}>{['low', 'medium', 'high', 'critical'].map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
      <fieldset><legend className="text-sm font-bold text-slate-700">Inspection areas</legend><p className="mt-1 text-xs text-slate-500">Suggested from the latest approved assessment. Deselect any area that is not required.</p><div className="mt-3 grid gap-2 sm:grid-cols-2">{(suggestedAreas.length ? suggestedAreas : ['General vehicle condition']).map((area) => <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-slate-200 p-3 text-sm font-semibold hover:bg-slate-50" key={area}><input checked={areas.includes(area)} onChange={(event) => setAreas((current) => event.target.checked ? [...current, area] : current.filter((item) => item !== area))} type="checkbox" />{area}</label>)}</div></fieldset>
      <label className="block text-sm font-bold text-slate-700">Operational note <span className="font-medium text-slate-400">(optional)</span><textarea className="mt-2 min-h-24 w-full resize-y rounded-lg border border-slate-300 p-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" onChange={(event) => setNotes(event.target.value)} placeholder="Add symptoms, access details, or timing requirements" value={notes} /></label>
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-800">Adding this vehicle creates an active service hold until the inspection workflow is resolved.</div>
      {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700" role="alert">{error}</div>}
    </ModalBody>
    <ModalFooter><SecondaryButton onClick={onClose}>Cancel</SecondaryButton><PrimaryButton disabled={busy} type="submit">{busy ? 'Adding...' : 'Add to inspection'}</PrimaryButton></ModalFooter>
  </form></ModalPanel></ModalViewport>
}
