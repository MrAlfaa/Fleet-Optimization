import { useEffect, useRef, useState, type ReactNode } from 'react'
import clsx from 'clsx'
import { CircleAlert, Info, TriangleAlert, X, type LucideIcon } from 'lucide-react'
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
    <section className={clsx('min-w-0 max-w-full rounded-lg border border-fleet-line bg-white shadow-card', className)}>
      {(title || action) && (
        <div className="flex min-h-14 min-w-0 flex-wrap items-center justify-between gap-3 border-b border-fleet-line/80 px-5 py-3.5">
          {title && <h2 className="text-[15px] font-bold text-fleet-ink">{title}</h2>}
          {action}
        </div>
      )}
      <div className="min-w-0 p-5">{children}</div>
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
    <div className="rounded-lg border border-fleet-line bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:shadow-soft">
      <div className="mb-4 flex items-center justify-between">
        <span className="text-[13px] font-semibold text-fleet-muted">{label}</span>
        <span className={clsx('grid h-9 w-9 place-items-center rounded-lg', tones[tone])}>
          <Icon className="h-5 w-5" />
        </span>
      </div>
      <div className="flex items-end gap-3">
        <div className="text-3xl font-bold tracking-normal">{value}</div>
        <div className={clsx('mb-1 rounded-md px-2 py-1 text-[11px] font-semibold', tone === 'red' ? 'bg-red-50 text-red-700' : 'bg-blue-50 text-blue-700')}>
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
  return <span className={clsx('inline-flex items-center rounded-md px-2 py-1 text-xs font-semibold ring-1', tones[tone])}>{children}</span>
}

export function OperationalInfo({
  title,
  children,
  severity = 'info',
  active = false,
}: {
  title: string
  children: ReactNode
  severity?: 'info' | 'warning' | 'critical'
  active?: boolean
}) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const Icon = severity === 'critical' ? TriangleAlert : severity === 'warning' ? CircleAlert : Info
  const tone = severity === 'critical' ? 'border-red-200 bg-red-50 text-red-700' : severity === 'warning' ? 'border-amber-200 bg-amber-50 text-amber-700' : 'border-blue-200 bg-blue-50 text-blue-700'

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => event.key === 'Escape' && setOpen(false)
    const closeOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('keydown', closeOnEscape)
    document.addEventListener('mousedown', closeOutside)
    return () => {
      document.removeEventListener('keydown', closeOnEscape)
      document.removeEventListener('mousedown', closeOutside)
    }
  }, [])

  return (
    <div className="relative inline-flex" ref={containerRef}>
      <button
        aria-expanded={open}
        aria-label={title}
        className={clsx('focus-ring grid h-10 w-10 place-items-center rounded-lg border shadow-sm transition hover:-translate-y-0.5', tone, active && 'animate-pulse motion-reduce:animate-none')}
        onClick={() => setOpen((value) => !value)}
        title={title}
        type="button"
      >
        <Icon className="h-5 w-5" />
      </button>
      {open && (
        <div aria-label={title} className="absolute right-0 top-12 z-40 w-[min(340px,calc(100vw-2rem))] rounded-lg border border-fleet-line bg-white p-4 text-left shadow-2xl" role="dialog">
          <div className="flex items-start justify-between gap-3">
            <div className="font-bold text-fleet-ink">{title}</div>
            <button aria-label="Close" className="rounded-md p-1 text-fleet-muted hover:bg-slate-100" onClick={() => setOpen(false)} type="button"><X className="h-4 w-4" /></button>
          </div>
          <div className="mt-2 text-sm font-medium leading-6 text-fleet-muted">{children}</div>
        </div>
      )}
    </div>
  )
}

export function PrimaryButton({
  children,
  disabled = false,
  onClick,
  type = 'button',
}: {
  children: ReactNode
  disabled?: boolean
  onClick?: () => void
  type?: 'button' | 'submit'
}) {
  return (
    <button
      className="focus-ring inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-fleet-blue px-4 py-2 text-sm font-semibold text-white shadow-soft transition hover:-translate-y-0.5 hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0"
      disabled={disabled}
      onClick={onClick}
      type={type}
    >
      {children}
    </button>
  )
}

export function SecondaryButton({ children, disabled = false, onClick }: { children: ReactNode; disabled?: boolean; onClick?: () => void }) {
  return (
    <button
      className="focus-ring inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-fleet-line bg-white px-4 py-2 text-sm font-semibold text-fleet-ink shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
      disabled={disabled}
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
    <div className="mb-6 flex min-w-0 max-w-full flex-col gap-4 md:flex-row md:flex-wrap md:items-end md:justify-between">
      <div className="min-w-0">
        {eyebrow && <div className="mb-2">{eyebrow}</div>}
        <h2 className="text-[28px] font-bold leading-tight tracking-normal text-fleet-ink">{title}</h2>
        <p className="mt-1.5 text-sm font-normal text-fleet-muted">{description}</p>
      </div>
      {action && <div className="flex max-w-full flex-wrap items-center gap-2">{action}</div>}
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
    <div className="relative min-w-0 max-w-full overflow-hidden rounded-lg border border-fleet-line bg-white shadow-card after:pointer-events-none after:absolute after:bottom-0 after:right-0 after:top-0 after:w-5 after:bg-gradient-to-l after:from-slate-200/45 after:to-transparent">
      <div className="max-w-full overflow-x-auto overscroll-x-contain">
        <table className="w-full min-w-max text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
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

export function LoadingState({ label = 'Loading backend data...' }: { label?: string }) {
  return (
    <div aria-label={label} aria-live="polite" role="status">
      <span className="sr-only">{label}</span>
      <div className="animate-pulse space-y-6 motion-reduce:animate-none" data-testid="loading-skeleton">
        <div className="space-y-3 py-1">
          <div className="h-7 w-56 rounded-md bg-slate-200" />
          <div className="h-3.5 w-full max-w-md rounded bg-slate-100" />
        </div>

        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {[0, 1, 2, 3].map((item) => (
            <div className="h-28 rounded-lg border border-fleet-line bg-white p-5 shadow-card" key={item}>
              <div className="mb-6 h-3 w-2/3 rounded bg-slate-100" />
              <div className="h-7 w-1/2 rounded-md bg-slate-200" />
            </div>
          ))}
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.6fr)_minmax(260px,0.8fr)]">
          <div className="min-h-64 rounded-lg border border-fleet-line bg-white p-5 shadow-card">
            <div className="mb-7 h-4 w-40 rounded bg-slate-200" />
            <div className="space-y-4">
              {[72, 88, 64, 80].map((width) => (
                <div className="flex items-center gap-4" key={width}>
                  <div className="h-9 w-9 shrink-0 rounded-lg bg-blue-50" />
                  <div className="h-3.5 rounded bg-slate-100" style={{ width: `${width}%` }} />
                </div>
              ))}
            </div>
          </div>
          <div className="min-h-64 rounded-lg border border-fleet-line bg-white p-5 shadow-card">
            <div className="mb-7 h-4 w-32 rounded bg-slate-200" />
            <div className="space-y-5">
              <div className="h-20 rounded-lg bg-slate-100" />
              <div className="h-20 rounded-lg bg-slate-100" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function EmptyState({ title = 'No records found', description = 'The backend returned an empty result for this view.' }: { title?: string; description?: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-fleet-line bg-white p-6 text-center shadow-card">
      <div className="text-base font-black text-fleet-ink">{title}</div>
      <p className="mt-1 text-sm font-semibold text-fleet-muted">{description}</p>
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-red-700 shadow-card">
      <div className="font-black">Backend request failed</div>
      <p className="mt-1 text-sm font-semibold">{message}</p>
      {onRetry && (
        <button className="mt-3 rounded-xl bg-white px-4 py-2 text-sm font-black text-red-700 ring-1 ring-red-200" onClick={onRetry} type="button">
          Retry
        </button>
      )}
    </div>
  )
}
