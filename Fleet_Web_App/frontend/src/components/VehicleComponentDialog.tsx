import { ArchiveRestore, BrainCircuit, Pencil, Plus, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { fleetService } from '../services/fleetService'
import type { EvPartCatalogItem, VehiclePart } from '../types'
import { buildPartOptions } from '../utils/evParts'
import { showToast } from '../utils/toast'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from './ModalLayout'
import { PrimaryButton, RiskBadge, SecondaryButton, StatusBadge } from './UI'

const PART_CONDITIONS = [
  { value: 'unknown', label: 'Unknown' },
  { value: 'healthy', label: 'Healthy' },
  { value: 'warning', label: 'Warning' },
  { value: 'critical', label: 'Critical' },
  { value: 'maintained', label: 'Maintained' },
] as const

const CUSTOM_CATEGORIES = [
  { value: 'battery', label: 'Battery' }, { value: 'thermal', label: 'Thermal' },
  { value: 'powertrain', label: 'Powertrain' }, { value: 'braking', label: 'Braking' },
  { value: 'wheels', label: 'Wheels and tires' }, { value: 'suspension', label: 'Suspension' },
  { value: 'charging', label: 'Charging' }, { value: 'other', label: 'Other' },
] as const

export function VehicleComponentDialog({ vehicleId, parts, part, onClose, onSaved, onCreateMaintenance }: { vehicleId: string; parts: VehiclePart[]; part?: VehiclePart | null; onClose: () => void; onSaved: () => void; onCreateMaintenance?: (part: VehiclePart) => void }) {
  const [editing, setEditing] = useState(!part)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [catalog, setCatalog] = useState<EvPartCatalogItem[]>([])
  const [catalogError, setCatalogError] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [selectedKey, setSelectedKey] = useState('')
  const options = useMemo(() => buildPartOptions(catalog, parts), [catalog, parts])
  const selectedOption = options.find((option) => option.key === selectedKey)
  const existingCatalogEntry = catalog.find((item) => item.name.toLowerCase() === part?.name.toLowerCase())
  const customPart = Boolean(part && !existingCatalogEntry)

  useEffect(() => {
    let active = true
    fleetService.getEvPartCatalog()
      .then((items) => { if (active) setCatalog(items) })
      .catch((reason) => { if (active) setCatalogError(reason instanceof Error ? reason.message : 'Unable to load EV parts catalogue') })
    return () => { active = false }
  }, [])

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError('')
    const form = new FormData(event.currentTarget)
    try {
      if (!part && selectedOption?.availability === 'archived' && selectedOption.existingPartId) {
        await fleetService.restoreVehiclePart(selectedOption.existingPartId)
      } else {
        const isOther = !part && selectedKey === 'other'
        const payload = {
          part_name: part ? (customPart ? String(form.get('custom_name') || '').trim() : part.name) : (isOther ? String(form.get('custom_name') || '').trim() : selectedOption?.name ?? ''),
          part_category: part ? (customPart ? String(form.get('custom_category') || '').trim() : part.category ?? existingCatalogEntry?.category ?? 'other') : (isOther ? String(form.get('custom_category') || '').trim() : selectedOption?.category ?? ''),
          status: String(form.get('status') || 'unknown'),
          notes: String(form.get('notes') || '').trim() || undefined,
        }
        if (part) await fleetService.updateVehiclePart(part.id, payload)
        else await fleetService.createVehiclePart(vehicleId, payload)
      }
      await onSaved(); onClose()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to save part')
    } finally { setBusy(false) }
  }

  const lifecycle = async () => {
    if (!part) return
    setBusy(true); setError('')
    try {
      if (part.isActive !== false) await fleetService.archiveVehiclePart(part.id, 'Deleted from vehicle workspace')
      else await fleetService.restoreVehiclePart(part.id)
      showToast(part.isActive !== false
        ? { tone: 'success', title: 'Part deleted', message: `${part.name} was removed from active monitoring. Its history is preserved.` }
        : { tone: 'success', title: 'Part restored', message: `${part.name} is active and available for monitoring again.` })
      await onSaved(); onClose()
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : 'Unable to update part'
      setError(message)
      setConfirmDelete(false)
      showToast({ tone: 'warning', title: 'Part was not deleted', message })
    } finally { setBusy(false) }
  }

  const noCataloguePartsAvailable = options.length > 0 && options.every((option) => option.availability === 'active')
  const selectedAction = selectedOption?.availability === 'archived' ? 'Restore part' : 'Save part'

  return <ModalViewport align="right">
    <ModalPanel aria-modal="true" className="h-full max-w-lg" role="dialog">
      <form className="contents" onSubmit={submit}>
        <ModalHeader className="flex items-start justify-between gap-4">
          <div><h2 className="text-xl font-extrabold">{part ? part.name : 'Add EV part'}</h2><p className="mt-1 text-sm text-slate-500">Part condition, service information, and predictive-maintenance relationship.</p></div>
          <button aria-label="Close part details" className="rounded-lg p-2 hover:bg-slate-100" onClick={onClose} type="button"><X className="h-5 w-5" /></button>
        </ModalHeader>
        <ModalBody>
          {part && !editing && <div className="space-y-5">
            {error && <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</p>}
            <div className="flex flex-wrap gap-2"><StatusBadge tone={part.isActive !== false ? 'green' : 'slate'}>{part.isActive !== false ? 'Active part' : 'Archived part'}</StatusBadge><StatusBadge tone={part.status === 'critical' ? 'red' : part.status === 'warning' ? 'amber' : part.status === 'healthy' || part.status === 'maintained' ? 'green' : 'slate'}>{part.status.replaceAll('_', ' ')}</StatusBadge></div>
            <section><h3 className="text-xs font-extrabold uppercase text-slate-500">Operational condition</h3><dl className="mt-2 grid grid-cols-2 gap-3"><Info label="Category" value={part.category ?? 'Other'} /><Info label="Condition" value={part.status} /><Info label="Last service" value={part.lastService} /><Info label="Predicted next" value={part.predictedNext} /></dl></section>
            <section className="rounded-lg border border-blue-100 bg-blue-50 p-4"><div className="flex items-center gap-2 font-extrabold text-blue-900"><BrainCircuit className="h-5 w-5" />ML-generated risk</div><div className="mt-3 flex items-center justify-between gap-3"><RiskBadge risk={part.risk} /><span aria-label={`${part.name} risk score ${Math.round(part.riskScore)} percent`} className="font-black text-blue-950">{Math.round(part.riskScore)}%</span></div><p className="mt-2 text-xs font-semibold text-blue-800">Risk is calculated by the predictive-maintenance service and cannot be edited manually.</p></section>
            <div className="rounded-lg bg-slate-50 p-4 text-sm text-slate-600">{part.note || 'No part notes.'}</div>
          </div>}
          {editing && <div className="space-y-4">
            {!part && <><label className="block text-sm font-bold text-slate-600">EV part<select className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 px-3" onChange={(event) => setSelectedKey(event.target.value)} required value={selectedKey}><option value="">Select a part</option>{options.map((option) => <option disabled={option.availability === 'active'} key={option.key} value={option.key}>{option.name}{option.availability === 'active' ? ' - Already added' : option.availability === 'archived' ? ' - Archived, restore available' : ''}</option>)}<option value="other">Other part</option></select></label>{noCataloguePartsAvailable && <p className="rounded-lg bg-emerald-50 p-3 text-sm font-semibold text-emerald-800">All predefined EV parts are already active. Select Other only for a legitimate additional vehicle part.</p>}</>}
            {part && !customPart && <ReadOnly label="Part" value={part.name} />}
            {((!part && selectedKey === 'other') || (part && customPart)) && <><Field defaultValue={part?.name} label="Custom part name" name="custom_name" /><Select defaultValue={part?.category ?? 'other'} label="Category" name="custom_category" options={CUSTOM_CATEGORIES} /></>}
            {selectedOption && selectedKey !== 'other' && <><ReadOnly label="Category" value={selectedOption.category} /><div className="rounded-lg border border-blue-100 bg-blue-50 p-3 text-sm"><div className="font-extrabold text-blue-900">Predictive-maintenance linked</div><p className="mt-1 text-blue-800">{selectedOption.description}. Signal group: {selectedOption.mlSignalGroup ?? 'general'}.</p></div></>}
            {!part && selectedKey === 'other' && <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-800">Custom parts are service-managed and are not directly evaluated by the current ML model.</p>}
            <Select defaultValue={part?.status ?? 'unknown'} label="Operational condition" name="status" options={PART_CONDITIONS} />
            <label className="block text-sm font-bold text-slate-600">Notes<textarea className="mt-2 min-h-28 w-full rounded-lg border border-slate-300 p-3" defaultValue={part?.note} name="notes" /></label>
            {catalogError && <p className="rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-700">{catalogError}</p>}
            {error && <p className="rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</p>}
          </div>}
        </ModalBody>
        <ModalFooter>
          {part && !editing ? <>{part.isActive === false ? <SecondaryButton disabled={busy} onClick={lifecycle}><ArchiveRestore className="h-4 w-4" />Restore part</SecondaryButton> : confirmDelete ? <><div className="mr-auto max-w-sm text-sm font-semibold text-red-700">Maintenance and prediction history will be preserved. Parts with open maintenance cannot be deleted.</div><SecondaryButton onClick={() => setConfirmDelete(false)}>Keep part</SecondaryButton><button className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-60" disabled={busy} onClick={lifecycle} type="button"><Trash2 className="h-4 w-4" />{busy ? 'Deleting...' : 'Confirm delete'}</button></> : <SecondaryButton disabled={busy} onClick={() => setConfirmDelete(true)}><Trash2 className="h-4 w-4" />Delete part</SecondaryButton>}{!confirmDelete && onCreateMaintenance && part.isActive !== false && <PrimaryButton onClick={() => onCreateMaintenance(part)}><Plus className="h-4 w-4" />Create maintenance</PrimaryButton>}{!confirmDelete && part.isActive !== false && <SecondaryButton onClick={() => setEditing(true)}><Pencil className="h-4 w-4" />Edit part</SecondaryButton>}</> : <><SecondaryButton onClick={part ? () => setEditing(false) : onClose}>Cancel</SecondaryButton><PrimaryButton disabled={busy || (!part && (!selectedKey || selectedOption?.availability === 'active'))} type="submit">{busy ? 'Saving...' : selectedAction}</PrimaryButton></>}
        </ModalFooter>
      </form>
    </ModalPanel>
  </ModalViewport>
}

function Field({ label, name, defaultValue }: { label: string; name: string; defaultValue?: string }) { return <label className="block text-sm font-bold text-slate-600">{label}<input className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 px-3" defaultValue={defaultValue} name={name} required /></label> }
function Select({ label, name, options, defaultValue }: { label: string; name: string; options: readonly { value: string; label: string }[]; defaultValue: string }) { return <label className="block text-sm font-bold text-slate-600">{label}<select className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 px-3" defaultValue={defaultValue} name={name}>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label> }
function ReadOnly({ label, value }: { label: string; value: string }) { return <div><div className="text-sm font-bold text-slate-600">{label}</div><div className="mt-2 flex min-h-11 items-center rounded-lg border border-slate-200 bg-slate-50 px-3 font-semibold capitalize text-slate-700">{value}</div></div> }
function Info({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border border-slate-200 p-3"><dt className="text-xs font-bold text-slate-500">{label}</dt><dd className="mt-1 break-words font-bold capitalize">{value}</dd></div> }
