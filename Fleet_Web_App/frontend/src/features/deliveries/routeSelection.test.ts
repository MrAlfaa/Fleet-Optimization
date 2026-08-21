import { beforeEach, describe, expect, it } from 'vitest'
import { consumeRouteDeliverySelection, saveRouteDeliverySelection } from './routeSelection'

describe('route delivery selection handoff', () => {
  beforeEach(() => sessionStorage.clear())
  it('deduplicates and consumes the selected delivery IDs once', () => {
    saveRouteDeliverySelection(['a', 'a', 'b'])
    expect(consumeRouteDeliverySelection()).toEqual(['a', 'b'])
    expect(consumeRouteDeliverySelection()).toEqual([])
  })
})
