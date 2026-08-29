import { describe, expect, it } from 'vitest'
import { canAccess, firstAccessiblePermission, togglePermission, visibleNavigation } from './permissions'

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

  it('keeps administrator access authoritative when a cached session has stale permissions', () => {
    const staleAdmin = {
      ...fleetManager,
      role: 'admin' as const,
      permissions: [],
    }

    expect(canAccess(staleAdmin, 'maintenance.history.view')).toBe(true)
    expect(canAccess(staleAdmin, 'maintenance.work_orders.view')).toBe(true)
    expect(canAccess(staleAdmin, 'vehicles.tab.overview')).toBe(true)
  })

  it('filters navigation entries without changing their order', () => {
    const entries = [
      { label: 'Dashboard', permission: 'dashboard.view' },
      { label: 'Routes', permission: 'routes.view' },
      { label: 'Vehicles', permission: 'vehicles.view' },
    ]

    expect(visibleNavigation(entries, fleetManager).map((entry) => entry.label)).toEqual(['Dashboard', 'Vehicles'])
  })

  it('adds a parent page when a child tab is enabled', () => {
    const metadata = {
      'vehicles.view': { key: 'vehicles.view', label: 'Vehicles', type: 'page' as const, description: '' },
      'vehicles.tab.activity': { key: 'vehicles.tab.activity', label: 'Activity', type: 'tab' as const, description: '', parent: 'vehicles.view' },
    }

    expect(togglePermission([], 'vehicles.tab.activity', true, metadata)).toEqual([
      'vehicles.tab.activity',
      'vehicles.view',
    ])
  })

  it('removes dependent tabs and actions when their page is disabled', () => {
    const metadata = {
      'vehicles.view': { key: 'vehicles.view', label: 'Vehicles', type: 'page' as const, description: '' },
      'vehicles.tab.activity': { key: 'vehicles.tab.activity', label: 'Activity', type: 'tab' as const, description: '', parent: 'vehicles.view' },
      'vehicles.update': { key: 'vehicles.update', label: 'Edit', type: 'action' as const, description: '', parent: 'vehicles.view' },
    }

    expect(togglePermission(Object.keys(metadata), 'vehicles.view', false, metadata)).toEqual([])
  })

  it('selects the first permitted workspace tab in business order', () => {
    expect(firstAccessiblePermission(
      ['vehicles.tab.overview', 'vehicles.tab.risk_assessment', 'vehicles.tab.activity'],
      ['vehicles.tab.activity', 'vehicles.tab.risk_assessment'],
    )).toBe('vehicles.tab.risk_assessment')
  })
})
