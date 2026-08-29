import type { PaginatedResponse, UserRole } from '../types'
import { apiClient } from './apiClient'
import type { PermissionMetadata } from '../utils/permissions'

export interface ManagedUser {
  id: string
  full_name: string
  email: string
  role: UserRole
  phone?: string | null
  is_active: boolean
  permissions: string[]
}

export interface PermissionCatalog {
  groups: Record<string, string[]>
  items: Record<string, PermissionMetadata>
  role_permissions: Record<UserRole, string[]>
}

type PermissionCatalogResponse = Omit<PermissionCatalog, 'items'> & { items?: Record<string, PermissionMetadata> }

const permissionLabel = (permission: string) => {
  const segments = permission.split('.')
  const source = segments.at(-1) === 'view' ? segments[0] : segments.at(-1)!
  return source
  .replaceAll('_', ' ')
  .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function normalizePermissionCatalog(catalog: PermissionCatalogResponse): PermissionCatalog {
  const items = { ...(catalog.items ?? {}) }
  for (const [group, permissions] of Object.entries(catalog.groups)) {
    for (const permission of permissions) {
      if (items[permission]) continue
      const type = permission.includes('.tab.') ? 'tab' : group.toLowerCase().includes('action') || !permission.endsWith('.view') ? 'action' : 'page'
      items[permission] = {
        key: permission,
        label: permissionLabel(permission),
        type,
        description: `Controls access to ${permissionLabel(permission).toLowerCase()}.`,
      }
    }
  }
  return { ...catalog, items }
}

export const userAdminService = {
  list: () => apiClient.get<PaginatedResponse<ManagedUser>>('/users', { query: { limit: 100 } }),
  catalog: async () => normalizePermissionCatalog(await apiClient.get<PermissionCatalogResponse>('/users/permissions/catalog')),
  create: (payload: { full_name: string; email: string; password: string; role: Exclude<UserRole, 'driver'>; phone?: string }) =>
    apiClient.post<ManagedUser>('/users', payload),
  setPermissions: (userId: string, permissions: string[]) => apiClient.put<ManagedUser>(`/users/${userId}/permissions`, { permissions }),
  setActive: (userId: string, active: boolean) => apiClient.patch<ManagedUser>(`/users/${userId}/${active ? 'activate' : 'deactivate'}`),
}
