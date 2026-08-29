const KEY = 'fleetopt.route-delivery-selection'
const CONTEXT_KEY = 'fleetopt.route-planning-context'

export interface RoutePlanningContext {
  vehicleId: string
  planId: string
  loadId: string
}

export function saveRouteDeliverySelection(ids: string[]) {
  sessionStorage.setItem(KEY, JSON.stringify([...new Set(ids.filter(Boolean))]))
}

export function consumeRouteDeliverySelection(): string[] {
  try {
    const value = JSON.parse(sessionStorage.getItem(KEY) || '[]')
    sessionStorage.removeItem(KEY)
    return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
  } catch {
    sessionStorage.removeItem(KEY)
    return []
  }
}

export function saveRoutePlanningContext(context: RoutePlanningContext) {
  sessionStorage.setItem(CONTEXT_KEY, JSON.stringify(context))
}

export function consumeRoutePlanningContext(): RoutePlanningContext | null {
  try {
    const value = JSON.parse(sessionStorage.getItem(CONTEXT_KEY) || 'null')
    sessionStorage.removeItem(CONTEXT_KEY)
    if (!value || typeof value.vehicleId !== 'string' || typeof value.planId !== 'string' || typeof value.loadId !== 'string') return null
    return value
  } catch {
    sessionStorage.removeItem(CONTEXT_KEY)
    return null
  }
}
