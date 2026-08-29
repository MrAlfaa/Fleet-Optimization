import type { VirtualLoad } from './types'

export interface CargoParcelDetail {
  parcelId: string
  dimensions: string
  position: string
  layer: number
  loadSequence: number | null
  handling: string[]
}

export function cargoParcelDetail(load: VirtualLoad, parcelId: string): CargoParcelDetail | null {
  const placement = load.placements.find((item) => item.parcel_id === parcelId)
  if (!placement) return null
  const sequenceIndex = load.loading_sequence.indexOf(parcelId)
  const handling = [
    placement.fragile ? 'Fragile' : null,
    placement.fixed_orientation ? 'Fixed orientation' : null,
  ].filter((value): value is string => Boolean(value))
  return {
    parcelId,
    dimensions: `${placement.length_cm} x ${placement.width_cm} x ${placement.height_cm} cm`,
    position: `${placement.x_cm}, ${placement.y_cm}, ${placement.z_cm} cm`,
    layer: placement.layer ?? 0,
    loadSequence: sequenceIndex >= 0 ? sequenceIndex + 1 : null,
    handling: handling.length ? handling : ['Standard handling'],
  }
}

export function cargoBayDimensions(load: VirtualLoad) {
  return {
    lengthCm: load.assigned_cargo_length_cm || load.cargo_length_cm || Math.max(...load.placements.map((item) => item.x_cm + item.length_cm), 320),
    widthCm: load.assigned_cargo_width_cm || load.cargo_width_cm || Math.max(...load.placements.map((item) => item.y_cm + item.width_cm), 180),
    heightCm: load.assigned_cargo_height_cm || load.cargo_height_cm || Math.max(...load.placements.map((item) => item.z_cm + item.height_cm), 170),
  }
}
