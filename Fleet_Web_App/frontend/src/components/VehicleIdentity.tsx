import { Truck } from 'lucide-react'
import type { Vehicle } from '../types'


const SIZE_STYLES = {
  sm: { image: 'h-11 w-14', title: 'text-sm', detail: 'text-xs' },
  md: { image: 'h-16 w-20', title: 'text-base', detail: 'text-xs' },
  lg: { image: 'h-24 w-32', title: 'text-2xl', detail: 'text-sm' },
} as const


export function VehicleIdentity({ vehicle, size = 'md' }: { vehicle: Vehicle; size?: keyof typeof SIZE_STYLES }) {
  const styles = SIZE_STYLES[size]
  return (
    <div className="flex min-w-0 items-center gap-3">
      <div className={`${styles.image} grid shrink-0 place-items-center overflow-hidden rounded-lg border border-slate-200 bg-slate-100`}>
        {vehicle.imageUrl ? (
          <img alt={`${vehicle.registrationNumber} vehicle`} className="h-full w-full object-cover" src={vehicle.imageUrl} />
        ) : (
          <Truck aria-hidden="true" className="h-1/2 w-1/2 text-slate-400" />
        )}
      </div>
      <div className="min-w-0">
        <div className={`${styles.title} truncate font-extrabold text-slate-950`}>{vehicle.registrationNumber}</div>
        <div className={`${styles.detail} truncate font-medium text-slate-500`}>{vehicle.vehicleCode} · {vehicle.category}</div>
      </div>
    </div>
  )
}
