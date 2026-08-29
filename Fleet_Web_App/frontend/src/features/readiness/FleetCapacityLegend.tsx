import type { ReadinessCapacityModel } from './readinessCapacity'

interface FleetCapacityLegendProps {
  capacity: ReadinessCapacityModel
}

const items = [
  { key: 'ready', label: 'ready', color: 'bg-emerald-500' },
  { key: 'warning', label: 'available with warnings', color: 'bg-amber-400' },
  { key: 'gap', label: 'capacity gap', color: 'border-2 border-red-500 bg-white' },
  { key: 'blocked', label: 'blocked', color: 'bg-slate-500' },
] as const

export function FleetCapacityLegend({ capacity }: FleetCapacityLegendProps) {
  return (
    <ul aria-label="Capacity status legend" className="flex flex-wrap gap-x-5 gap-y-2 text-xs font-semibold text-slate-600">
      {items.map((item) => (
        <li className="flex items-center gap-2" key={item.key}>
          <span aria-hidden="true" className={`h-3 w-3 rounded-sm ${item.color}`} />
          <span>{capacity[item.key]} {item.label}</span>
        </li>
      ))}
    </ul>
  )
}
