import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { UserManagementPage } from './UserManagementPage'
import { userAdminService } from '../services/userAdminService'

vi.mock('../services/userAdminService', () => ({
  userAdminService: {
    list: vi.fn(),
    catalog: vi.fn(),
    create: vi.fn(),
    setPermissions: vi.fn(),
    setActive: vi.fn(),
  },
}))

const users = [
  { id: 'admin-1', full_name: 'Admin User', email: 'admin@example.com', role: 'admin' as const, is_active: true, permissions: ['dashboard.view', 'permissions.manage', 'routes.dispatch'] },
  { id: 'maint-1', full_name: 'Maintenance User', email: 'maint@example.com', role: 'maintenance_manager' as const, is_active: true, permissions: ['maintenance.view'] },
]

const catalog = {
  groups: {
    'Workspace pages': ['dashboard.view'],
    'Fleet pages': ['maintenance.view'],
    'Operational actions': ['routes.dispatch'],
    Administration: ['permissions.manage'],
  },
  items: {
    'dashboard.view': { key: 'dashboard.view', label: 'Dashboard', type: 'page' as const, description: 'Open dashboard' },
    'maintenance.view': { key: 'maintenance.view', label: 'Maintenance Command Center', type: 'page' as const, description: 'Open maintenance' },
    'routes.view': { key: 'routes.view', label: 'Route Planning', type: 'page' as const, description: 'Open routes' },
    'routes.dispatch': { key: 'routes.dispatch', label: 'Dispatch routes', type: 'action' as const, description: 'Dispatch routes', parent: 'routes.view' },
    'permissions.manage': { key: 'permissions.manage', label: 'Access Control', type: 'action' as const, description: 'Manage access' },
  },
  role_permissions: {
    admin: ['dashboard.view', 'maintenance.view', 'routes.dispatch', 'permissions.manage'],
    fleet_manager: ['dashboard.view'],
    maintenance_manager: ['maintenance.view'],
    route_planner: ['routes.dispatch'],
    driver: [],
  },
}

describe('UserManagementPage', () => {
  beforeEach(() => {
    vi.mocked(userAdminService.list).mockResolvedValue({ items: users, page: 1, limit: 100, total: 2, pages: 1 })
    vi.mocked(userAdminService.catalog).mockResolvedValue(catalog)
    vi.mocked(userAdminService.setPermissions).mockImplementation(async (id, permissions) => ({ ...users.find((user) => user.id === id)!, permissions }))
  })

  it('allows a non-admin user to receive permissions outside the role template', async () => {
    render(<UserManagementPage />)
    fireEvent.click(await screen.findByRole('button', { name: /Maintenance User/i }))
    fireEvent.click(screen.getByRole('tab', { name: 'Actions' }))

    const dispatch = screen.getByRole('checkbox', { name: /Dispatch routes/i })
    expect(dispatch).not.toBeChecked()
    fireEvent.click(dispatch)
    fireEvent.click(screen.getByRole('button', { name: /Save access policy/i }))

    await waitFor(() => expect(userAdminService.setPermissions).toHaveBeenCalledWith(
      'maint-1',
      expect.arrayContaining(['routes.dispatch', 'routes.view']),
    ))
  })

  it('renders every administrator permission as protected', async () => {
    render(<UserManagementPage />)
    fireEvent.click(await screen.findByRole('button', { name: /Admin User/i }))

    expect(screen.getByText(/Administrator access is protected/i)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Save access policy/i })).not.toBeInTheDocument()
  })
})
