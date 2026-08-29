import type { ReadinessCapacityModel } from './readinessCapacity'

interface FleetCapacityFallbackProps {
  capacity: ReadinessCapacityModel
}

const MAX_VISIBLE_SLOTS = 30

export function FleetCapacityFallback({ capacity }: FleetCapacityFallbackProps) {
  const slotCount = Math.min(capacity.required, MAX_VISIBLE_SLOTS)
  const filledCount = Math.min(capacity.eligible, slotCount)
  const warningCount = Math.min(capacity.warning, filledCount)
  const readyCount = filledCount - warningCount

  return (
    <div
      className="flex h-full flex-col justify-between overflow-hidden bg-slate-50 p-4 sm:p-5"
      data-testid="capacity-css-fallback"
    >
      <div>
        <p className="text-xs font-bold uppercase text-slate-500">Capacity overview</p>
        <div className="mt-4 grid grid-cols-6 gap-2 sm:grid-cols-10">
          {Array.from({ length: slotCount }, (_, index) => {
            const state = index < readyCount ? 'ready' : index < filledCount ? 'warning' : 'gap'
            const style = state === 'ready'
              ? 'border-emerald-600 bg-emerald-500'
              : state === 'warning'
                ? 'border-amber-500 bg-amber-400'
                : 'border-red-500 bg-white'
            return <span aria-hidden="true" className={`aspect-square rounded-sm border-2 ${style}`} key={index} />
          })}
        </div>
      </div>
      <p className="text-xs text-slate-500">
        {capacity.required > MAX_VISIBLE_SLOTS
          ? `Showing ${MAX_VISIBLE_SLOTS} of ${capacity.required} required positions. Exact totals are listed above.`
          : 'Simplified view shown because 3D graphics are unavailable.'}
      </p>
    </div>
  )
}
