const KEY = 'fleetopt.route-delivery-selection'

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
