import { describe, expect, it } from 'vitest'
import { canAccess, visibleNavigation } from './permissions'

const fleetManager = {
  id: '1',
  name: 'Fleet Manager',
  email: 'fleet@example.com',
  role: 'fleet_manager' as const,
  organization: 'FleetOpt AI',
  permissions: ['dashboard.view', 'vehicles.view'],
}

describe('permission helpers', () => {
  it('uses backend-provided effective permissions', () => {
    expect(canAccess(fleetManager, 'vehicles.view')).toBe(true)
    expect(canAccess(fleetManager, 'routes.dispatch')).toBe(false)
  })

  it('filters navigation entries without changing their order', () => {
    const entries = [
      { label: 'Dashboard', permission: 'dashboard.view' },
      { label: 'Routes', permission: 'routes.view' },
      { label: 'Vehicles', permission: 'vehicles.view' },
    ]

    expect(visibleNavigation(entries, fleetManager).map((entry) => entry.label)).toEqual(['Dashboard', 'Vehicles'])
  })
})
