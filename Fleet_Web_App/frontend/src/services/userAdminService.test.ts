import { describe, expect, it } from 'vitest'
import { normalizePermissionCatalog } from './userAdminService'

describe('normalizePermissionCatalog', () => {
  it('keeps the access screen usable with the legacy catalog response', () => {
    const catalog = normalizePermissionCatalog({
      groups: { 'Workspace pages': ['dashboard.view'], 'Operational actions': ['routes.dispatch'] },
      role_permissions: { admin: ['dashboard.view', 'routes.dispatch'], fleet_manager: [], maintenance_manager: [], route_planner: [], driver: [] },
    })

    expect(catalog.items['dashboard.view']).toMatchObject({ label: 'Dashboard', type: 'page' })
    expect(catalog.items['routes.dispatch']).toMatchObject({ label: 'Dispatch', type: 'action' })
  })
})
