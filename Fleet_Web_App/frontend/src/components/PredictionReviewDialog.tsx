import { ShieldCheck, ShieldX, X } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { fleetService } from '../services/fleetService'
import type { MaintenanceReview } from '../types'
import { PrimaryButton, SecondaryButton } from './UI'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from './ModalLayout'

export function PredictionReviewDialog({ review, onClose, onResolved }: { review: MaintenanceReview; onClose: () => void; onResolved: () => Promise<void> | void }) {
  const [resolution, setResolution] = useState<'cleared' | 'confirmed'>('cleared')
  const [notes, setNotes] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (notes.trim().length < 10) { setError('Add at least 10 characters of inspection evidence.'); return }
    setBusy(true); setError('')
    try { await fleetService.resolvePredictionReview(review.id, resolution, notes.trim()); await onResolved(); onClose() }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to resolve engineering review') }
    finally { setBusy(false) }
  }
  return <ModalViewport><ModalPanel aria-modal="true" className="max-w-xl" role="dialog"><form className="contents" onSubmit={submit}><ModalHeader className="flex items-start justify-between gap-4"><div><h2 className="text-xl font-extrabold">Resolve engineering review</h2><p className="mt-1 text-sm text-slate-500">{review.vehicleRegistration}</p></div><button aria-label="Close review dialog" className="rounded-lg p-2 hover:bg-slate-100" onClick={onClose} type="button"><X className="h-5 w-5" /></button></ModalHeader><ModalBody className="space-y-5"><div className="grid gap-3 sm:grid-cols-2"><label className={`cursor-pointer rounded-lg border p-4 ${resolution === 'cleared' ? 'border-emerald-500 bg-emerald-50' : 'border-slate-200'}`}><input checked={resolution === 'cleared'} className="sr-only" name="resolution" onChange={() => setResolution('cleared')} type="radio" /><ShieldCheck className="h-5 w-5 text-emerald-700" /><div className="mt-2 font-extrabold">Clear for dispatch</div><p className="mt-1 text-xs text-slate-600">Inspection found no issue for this exact snapshot.</p></label><label className={`cursor-pointer rounded-lg border p-4 ${resolution === 'confirmed' ? 'border-red-500 bg-red-50' : 'border-slate-200'}`}><input checked={resolution === 'confirmed'} className="sr-only" name="resolution" onChange={() => setResolution('confirmed')} type="radio" /><ShieldX className="h-5 w-5 text-red-700" /><div className="mt-2 font-extrabold">Confirm issue</div><p className="mt-1 text-xs text-slate-600">Keep the hold until linked maintenance is completed.</p></label></div><label className="block text-sm font-bold text-slate-700">Inspection evidence<textarea className="mt-2 min-h-28 w-full rounded-lg border border-slate-300 p-3 font-medium outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" onChange={(event) => setNotes(event.target.value)} placeholder="Record checks performed and the engineering conclusion." value={notes} /></label>{error && <div className="rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-700" role="alert">{error}</div>}</ModalBody><ModalFooter><SecondaryButton onClick={onClose}>Cancel</SecondaryButton><PrimaryButton disabled={busy} type="submit">{busy ? 'Saving review...' : resolution === 'cleared' ? 'Clear vehicle' : 'Confirm issue'}</PrimaryButton></ModalFooter></form></ModalPanel></ModalViewport>
}
