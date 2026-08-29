import { AlertTriangle, CheckCircle2, CircleSlash2 } from 'lucide-react'
import type { InspectionCheckOutcome } from '../types'
import type { InspectionChecklistFormItem } from '../features/maintenance/inspectionChecklist'

export function InspectionChecklist({ items, onChange, readOnly = false, errors = {} }: {
  items: InspectionChecklistFormItem[]
  onChange: (items: InspectionChecklistFormItem[]) => void
  readOnly?: boolean
  errors?: Record<string, string>
}) {
  const update = (key: string, changes: Partial<InspectionChecklistFormItem>) => {
    onChange(items.map((item) => item.key === key ? { ...item, ...changes } : item))
  }

  return <div className="grid min-w-0 gap-4 xl:grid-cols-2">
    {items.map((item) => <section className="min-w-0 rounded-lg border border-slate-200 bg-white p-4 shadow-sm" key={item.key}>
      <div className="flex min-w-0 items-start justify-between gap-3">
        <h3 className="min-w-0 font-extrabold text-slate-950">{item.label}</h3>
        {readOnly && item.outcome && <OutcomeLabel outcome={item.outcome} />}
      </div>
      {!readOnly && <fieldset className="mt-4">
        <legend className="sr-only">{item.label} outcome</legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {outcomeOptions.map(({ value, label, icon: Icon }) => <label className={`flex min-h-11 cursor-pointer items-center gap-2 rounded-lg border px-3 text-sm font-bold transition ${item.outcome === value ? 'border-blue-500 bg-blue-50 text-blue-800' : 'border-slate-200 hover:bg-slate-50'}`} key={value}>
            <input checked={item.outcome === value} className="sr-only" name={`outcome-${item.key}`} onChange={() => update(item.key, { outcome: value })} type="radio" />
            <Icon className="h-4 w-4 shrink-0" />{label}
          </label>)}
        </div>
      </fieldset>}
      {(item.outcome === 'failed' || (readOnly && item.remark)) && (readOnly
        ? <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-800">{item.remark || 'No remark recorded'}</p>
        : <label className="mt-4 block text-sm font-bold text-slate-700">Issue remark<textarea aria-label={`${item.label} remark`} className="mt-2 min-h-24 w-full rounded-lg border border-slate-300 p-3 font-medium outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" onChange={(event) => update(item.key, { remark: event.target.value })} placeholder="Describe the condition and evidence found." value={item.remark} /></label>)}
      {errors[item.key] && <p className="mt-2 text-sm font-semibold text-red-700" role="alert">{errors[item.key]}</p>}
    </section>)}
  </div>
}

const outcomeOptions = [
  { value: 'passed' as const, label: 'Passed', icon: CheckCircle2 },
  { value: 'failed' as const, label: 'Issue found', icon: AlertTriangle },
  { value: 'not_applicable' as const, label: 'Not applicable', icon: CircleSlash2 },
]

function OutcomeLabel({ outcome }: { outcome: InspectionCheckOutcome }) {
  const label = outcome === 'failed' ? 'Issue found' : outcome === 'not_applicable' ? 'Not applicable' : 'Passed'
  return <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-bold ${outcome === 'failed' ? 'bg-red-100 text-red-800' : outcome === 'passed' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'}`}>{label}</span>
}
