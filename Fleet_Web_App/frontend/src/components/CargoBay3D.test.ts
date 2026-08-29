import { describe, expect, it } from 'vitest'
import { cargoBayDimensions, cargoParcelDetail } from '../features/loadOptimization/cargoBay'
import type { VirtualLoad } from '../features/loadOptimization/types'

describe('cargoBayDimensions', () => {
  it('uses the registered cargo bay instead of inferring the vehicle body from parcels', () => {
    const load = {
      cargo_length_cm: 540,
      cargo_width_cm: 220,
      cargo_height_cm: 210,
      placements: [{ x_cm: 0, y_cm: 0, z_cm: 0, length_cm: 40, width_cm: 30, height_cm: 20 }],
    } as VirtualLoad

    expect(cargoBayDimensions(load)).toEqual({ lengthCm: 540, widthCm: 220, heightCm: 210 })
  })

  it('uses the confirmed physical vehicle bay after assignment', () => {
    const load = {
      cargo_length_cm: 310,
      cargo_width_cm: 170,
      cargo_height_cm: 160,
      assigned_cargo_length_cm: 320,
      assigned_cargo_width_cm: 170,
      assigned_cargo_height_cm: 175,
      placements: [],
    } as unknown as VirtualLoad

    expect(cargoBayDimensions(load)).toEqual({ lengthCm: 320, widthCm: 170, heightCm: 175 })
  })

  it('builds user-facing parcel details with loading order and handling rules', () => {
    const load = {
      placements: [{
        parcel_id: 'parcel-22', x_cm: 15, y_cm: 20, z_cm: 40,
        length_cm: 60, width_cm: 45, height_cm: 35, fragile: true,
        fixed_orientation: true, layer: 2,
      }],
      loading_sequence: ['parcel-10', 'parcel-22'],
    } as VirtualLoad

    expect(cargoParcelDetail(load, 'parcel-22')).toEqual({
      parcelId: 'parcel-22',
      dimensions: '60 x 45 x 35 cm',
      position: '15, 20, 40 cm',
      layer: 2,
      loadSequence: 2,
      handling: ['Fragile', 'Fixed orientation'],
    })
    expect(cargoParcelDetail(load, 'missing')).toBeNull()
  })
})
