import { describe, expect, it } from 'vitest'
import { buildOptimizationPayload } from './optimizationPayload'

describe('buildOptimizationPayload', () => {
  it('uses only explicitly selected delivery IDs', () => {
    const payload = buildOptimizationPayload({
      deliveryOrderIds: ['order-a', 'order-b'],
      driverId: 'driver-1',
      vehicleId: 'vehicle-1',
    })

    expect(payload.delivery_order_ids).toEqual(['order-a', 'order-b'])
    expect(payload).not.toHaveProperty('delivery_stops')
    expect(payload).not.toHaveProperty('depot_latitude')
    expect(payload).not.toHaveProperty('depot_longitude')
  })

  it('includes an approved load-plan context when supplied', () => {
    const payload = buildOptimizationPayload({
      deliveryOrderIds: ['order-a'],
      driverId: 'driver-1',
      vehicleId: 'vehicle-1',
      loadContext: { planId: 'plan-1', loadId: 'load-1' },
    })

    expect(payload).toMatchObject({ load_plan_id: 'plan-1', load_id: 'load-1' })
  })

  it.each([
    { deliveryOrderIds: [], driverId: 'driver-1', vehicleId: 'vehicle-1' },
    { deliveryOrderIds: ['order-a'], driverId: '', vehicleId: 'vehicle-1' },
    { deliveryOrderIds: ['order-a'], driverId: 'driver-1', vehicleId: '' },
  ])('rejects an incomplete assignment wizard', (input) => {
    expect(() => buildOptimizationPayload(input)).toThrow(/select/i)
  })
})
