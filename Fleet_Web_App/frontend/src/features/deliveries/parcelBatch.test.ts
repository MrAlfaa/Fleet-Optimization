import { describe, expect, it } from 'vitest'
import type { DeliveryOrder } from '../../types'
import { updateParcelBatchSelection } from './parcelBatch'

const parcel = (id: string, deliveryDate: string, deliveryPeriod: 'first_half' | 'second_half'): DeliveryOrder => ({
  id,
  orderCode: id,
  customer: 'Customer',
  priority: 'Standard',
  timeWindow: deliveryDate,
  zone: 'Colombo Central',
  location: 'Colombo',
  status: 'Unassigned',
  backendStatus: 'pending',
  deliveryDate,
  deliveryPeriod,
})

describe('updateParcelBatchSelection', () => {
  it('selects parcels from the same delivery date and period', () => {
    const parcels = [parcel('a', '2026-08-30', 'first_half'), parcel('b', '2026-08-30', 'first_half')]

    const result = updateParcelBatchSelection([], parcels[0], parcels)
    const next = updateParcelBatchSelection(result.selectedIds, parcels[1], parcels)

    expect(next).toEqual({ selectedIds: ['a', 'b'], error: null })
  })

  it('rejects a parcel from a different delivery period', () => {
    const parcels = [parcel('a', '2026-08-30', 'first_half'), parcel('b', '2026-08-30', 'second_half')]

    const result = updateParcelBatchSelection(['a'], parcels[1], parcels)

    expect(result.selectedIds).toEqual(['a'])
    expect(result.error).toMatch(/same delivery date and period/i)
  })

  it('allows a selected parcel to be removed', () => {
    const parcels = [parcel('a', '2026-08-30', 'first_half')]

    expect(updateParcelBatchSelection(['a'], parcels[0], parcels)).toEqual({ selectedIds: [], error: null })
  })
})
