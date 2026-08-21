import { Truck } from 'lucide-react'

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-white/12 text-white ring-1 ring-white/15">
        <Truck className="h-5 w-5" />
      </div>
      {!compact && (
        <div>
          <div className="text-lg font-bold leading-tight tracking-normal text-white">FleetOpt AI</div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-blue-100/80">
            Logistics Intelligence
          </div>
        </div>
      )}
    </div>
  )
}
