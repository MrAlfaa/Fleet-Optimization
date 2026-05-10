import type { ReactNode } from 'react'
import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'
import type { RiskLevel } from '../types'
import { riskBadgeClass } from '../utils/format'

export function Card({
  title,
  action,
  children,
  className,
}: {
  title?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={clsx('rounded-2xl border border-fleet-line bg-white shadow-card', className)}>
      {(title || action) && (
        <div className="flex items-center justify-between border-b border-fleet-line/80 px-5 py-4">
          {title && <h2 className="text-base font-extrabold text-fleet-ink">{title}</h2>}
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  )
}

export function MetricCard({
  label,
  value,
  trend,
  icon: Icon,
  tone = 'blue',
}: {
  label: string
  value: string
  trend: string
  icon: LucideIcon
  tone?: 'blue' | 'green' | 'amber' | 'red'
}) {
  const tones = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    red: 'bg-red-50 text-red-700',
  }
  return (
    <div className="rounded-2xl border border-fleet-line bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:shadow-soft">
      <div className="mb-5 flex items-center justify-between">
        <span className="text-sm font-bold text-fleet-muted">{label}</span>
        <span className={clsx('grid h-10 w-10 place-items-center rounded-xl', tones[tone])}>
          <Icon className="h-5 w-5" />
        </span>
      </div>
      <div className="flex items-end gap-3">
        <div className="text-3xl font-black tracking-tight">{value}</div>
        <div className={clsx('mb-1 rounded-md px-2 py-1 text-xs font-bold', tone === 'red' ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700')}>
          {trend}
        </div>
      </div>
    </div>
  )
}

export function RiskBadge({ risk }: { risk: RiskLevel }) {
  return <span className={riskBadgeClass(risk)}>{risk}</span>
}

export function StatusBadge({ children, tone = 'blue' }: { children: ReactNode; tone?: 'blue' | 'green' | 'amber' | 'red' | 'slate' }) {
  const tones = {
    blue: 'bg-blue-50 text-blue-700 ring-blue-200',
    green: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
    amber: 'bg-amber-50 text-amber-700 ring-amber-200',
    red: 'bg-red-50 text-red-700 ring-red-200',
    slate: 'bg-slate-100 text-slate-600 ring-slate-200',
  }
  return <span className={clsx('inline-flex items-center rounded-md px-2 py-1 text-xs font-bold ring-1', tones[tone])}>{children}</span>
}

export function PrimaryButton({ children, onClick, type = 'button' }: { children: ReactNode; onClick?: () => void; type?: 'button' | 'submit' }) {
  return (
    <button
      className="focus-ring inline-flex items-center justify-center gap-2 rounded-xl bg-fleet-blue px-4 py-2.5 text-sm font-extrabold text-white shadow-soft transition hover:-translate-y-0.5 hover:bg-blue-700"
      onClick={onClick}
      type={type}
    >
      {children}
    </button>
  )
}

export function SecondaryButton({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  return (
    <button
      className="focus-ring inline-flex items-center justify-center gap-2 rounded-xl border border-fleet-line bg-white px-4 py-2.5 text-sm font-bold text-fleet-ink shadow-sm transition hover:bg-slate-50"
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  )
}

export function PageHeader({
  title,
  description,
  action,
  eyebrow,
}: {
  title: string
  description: string
  action?: ReactNode
  eyebrow?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        {eyebrow && <div className="mb-2">{eyebrow}</div>}
        <h2 className="text-3xl font-black tracking-tight text-fleet-ink">{title}</h2>
        <p className="mt-1 text-sm font-medium text-fleet-muted">{description}</p>
      </div>
      {action}
    </div>
  )
}

export function DataTable({
  headers,
  children,
}: {
  headers: string[]
  children: ReactNode
}) {
  return (
    <div className="overflow-hidden rounded-2xl border border-fleet-line bg-white shadow-card">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-100 text-xs font-black uppercase tracking-wide text-slate-500">
            <tr>
              {headers.map((header) => (
                <th className="px-5 py-3" key={header}>
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-fleet-line">{children}</tbody>
        </table>
      </div>
    </div>
  )
}

export function MapPanel({ children, className }: { children?: ReactNode; className?: string }) {
  return (
    <div className={clsx('map-grid relative min-h-[360px] overflow-hidden rounded-2xl border border-slate-300 shadow-inner', className)}>
      <div className="absolute inset-0 bg-slate-900/16" />
      <div className="absolute left-[14%] top-[55%] h-2 w-[62%] -rotate-12 rounded-full bg-white/70 shadow-[0_0_20px_rgba(255,255,255,0.5)]" />
      <div className="absolute left-[42%] top-[25%] h-2 w-[46%] rotate-45 rounded-full bg-white/50" />
      <div className="absolute left-[18%] top-[62%] h-4 w-4 rounded-full bg-red-500 ring-4 ring-white" />
      <div className="absolute left-[52%] top-[42%] h-4 w-4 rounded-full bg-blue-600 ring-4 ring-white" />
      <div className="absolute right-4 top-4 rounded-xl bg-white/80 px-3 py-2 text-xs font-bold text-slate-600 shadow">Simulated operations map</div>
      {children}
    </div>
  )
}
