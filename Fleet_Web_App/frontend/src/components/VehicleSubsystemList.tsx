import { BatteryCharging, ChevronRight, CircleDot, Cog, Disc3, Fan, Gauge, PlugZap, Snowflake, Thermometer, Wrench } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { VehiclePart } from '../types'
import { RiskBadge } from './UI'


function partIcon(name: string): LucideIcon {
  const value = name.toLowerCase()
  if (value.includes('cooling')) return Snowflake
  if (value.includes('battery')) return BatteryCharging
  if (value.includes('brake')) return Disc3
  if (value.includes('tire')) return CircleDot
  if (value.includes('charging')) return PlugZap
  if (value.includes('thermal')) return Thermometer
  if (value.includes('inverter') || value.includes('controller')) return Gauge
  if (value.includes('motor') || value.includes('drivetrain')) return Cog
  if (value.includes('suspension')) return Fan
  return Wrench
}


const riskBar = { low: 'bg-emerald-500', medium: 'bg-amber-400', high: 'bg-orange-500', critical: 'bg-red-500' }


export function VehicleSubsystemList({ parts, onSelectPart }: { parts: VehiclePart[]; onSelectPart: (part: VehiclePart) => void }) {
  return <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
    <div className="hidden grid-cols-[minmax(220px,1.4fr)_110px_minmax(140px,1fr)_150px_150px_32px] gap-4 border-b border-slate-200 bg-slate-50 px-5 py-3 text-xs font-bold uppercase text-slate-500 lg:grid">
      <span>EV part</span><span>Status</span><span>Risk score</span><span>Last service</span><span>Predicted next</span><span />
    </div>
    <div className="divide-y divide-slate-200">
      {parts.map((part) => {
        const Icon = partIcon(part.name)
        const slug = part.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '')
        const score = Math.min(100, Math.max(0, part.riskScore))
        return <button className={`grid w-full items-center gap-3 px-5 py-4 text-left transition hover:bg-blue-50/60 lg:grid-cols-[minmax(220px,1.4fr)_110px_minmax(140px,1fr)_150px_150px_32px] lg:gap-4 ${part.risk === 'critical' ? 'bg-red-50/50' : part.risk === 'high' ? 'bg-orange-50/40' : ''}`} data-testid={`subsystem-${slug}`} key={part.id} onClick={() => onSelectPart(part)} type="button">
          <span className="flex min-w-0 items-center gap-3"><span className={`grid h-10 w-10 shrink-0 place-items-center rounded-lg ${part.risk === 'critical' ? 'bg-red-100 text-red-700 motion-safe:animate-pulse motion-reduce:animate-none' : 'bg-blue-50 text-blue-700'}`}><Icon className="h-5 w-5" /></span><span className="min-w-0"><span className="block truncate font-extrabold text-slate-950">{part.name}</span><span className="block truncate text-xs font-medium capitalize text-slate-500">{part.status.replaceAll('_', ' ')}</span></span></span>
          <span><RiskBadge risk={part.risk} /></span>
          <span className="min-w-0"><span className="mb-1 flex justify-between text-xs font-bold text-slate-500"><span>{Math.round(score)}%</span><span>{part.risk}</span></span><span aria-label={`${part.name} risk score ${Math.round(score)} percent`} aria-valuemax={100} aria-valuemin={0} aria-valuenow={score} className="block h-2 overflow-hidden rounded-full bg-slate-100" role="progressbar"><span className={`block h-full rounded-full ${riskBar[part.risk]}`} style={{ width: `${score}%` }} /></span></span>
          <span className="text-sm font-semibold text-slate-700"><span className="mr-2 text-xs font-bold text-slate-400 lg:hidden">Last</span>{part.lastService}</span>
          <span className="text-sm font-semibold text-slate-700"><span className="mr-2 text-xs font-bold text-slate-400 lg:hidden">Next</span>{part.predictedNext}</span>
          <ChevronRight className="h-4 w-4 justify-self-end text-slate-400" />
        </button>
      })}
    </div>
  </div>
}
