import type { PaginatedResponse, UserRole } from '../types'
import { apiClient } from './apiClient'

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
  role_permissions: Record<UserRole, string[]>
}

export const userAdminService = {
  list: () => apiClient.get<PaginatedResponse<ManagedUser>>('/users', { query: { limit: 100 } }),
  catalog: () => apiClient.get<PermissionCatalog>('/users/permissions/catalog'),
  create: (payload: { full_name: string; email: string; password: string; role: Exclude<UserRole, 'driver'>; phone?: string }) =>
    apiClient.post<ManagedUser>('/users', payload),
  setPermissions: (userId: string, permissions: string[]) => apiClient.put<ManagedUser>(`/users/${userId}/permissions`, { permissions }),
  setActive: (userId: string, active: boolean) => apiClient.patch<ManagedUser>(`/users/${userId}/${active ? 'activate' : 'deactivate'}`),
}
