import { beforeEach, describe, expect, it } from 'vitest'
import { consumeRouteDeliverySelection, consumeRoutePlanningContext, saveRouteDeliverySelection, saveRoutePlanningContext } from './routeSelection'

describe('route delivery selection handoff', () => {
  beforeEach(() => sessionStorage.clear())
  it('deduplicates and consumes the selected delivery IDs once', () => {
    saveRouteDeliverySelection(['a', 'a', 'b'])
    expect(consumeRouteDeliverySelection()).toEqual(['a', 'b'])
    expect(consumeRouteDeliverySelection()).toEqual([])
  })

  it('hands an approved load context to route planning once', () => {
    saveRoutePlanningContext({ vehicleId: 'vehicle-1', planId: 'plan-1', loadId: 'load-1' })
    expect(consumeRoutePlanningContext()).toEqual({ vehicleId: 'vehicle-1', planId: 'plan-1', loadId: 'load-1' })
    expect(consumeRoutePlanningContext()).toBeNull()
  })
})
