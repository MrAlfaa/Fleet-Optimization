import type { DeliveryOrder } from '../../types'

export type DeliveryPeriod = 'first_half' | 'second_half'

export const DELIVERY_PERIOD_LABELS: Record<DeliveryPeriod, string> = {
  first_half: 'First Half · 08:00–12:00',
  second_half: 'Second Half · 13:00–17:00',
}

export function parcelBatchKey(parcel: DeliveryOrder) {
  return parcel.deliveryDate && parcel.deliveryPeriod
    ? `${parcel.deliveryDate}:${parcel.deliveryPeriod}`
    : ''
}

export function updateParcelBatchSelection(
  selectedIds: string[],
  parcel: DeliveryOrder,
  parcels: DeliveryOrder[],
): { selectedIds: string[]; error: string | null } {
  if (selectedIds.includes(parcel.id)) {
    return { selectedIds: selectedIds.filter((id) => id !== parcel.id), error: null }
  }

  const parcelKey = parcelBatchKey(parcel)
  const selectedParcels = new Map(parcels.map((item) => [item.id, item]))
  const activeKey = selectedIds.map((id) => selectedParcels.get(id)).filter(Boolean).map((item) => parcelBatchKey(item as DeliveryOrder)).find(Boolean)
  if (!parcelKey || (activeKey && activeKey !== parcelKey)) {
    return {
      selectedIds,
      error: 'Select parcels from the same delivery date and period for one route batch.',
    }
  }

  return { selectedIds: [...selectedIds, parcel.id], error: null }
}
