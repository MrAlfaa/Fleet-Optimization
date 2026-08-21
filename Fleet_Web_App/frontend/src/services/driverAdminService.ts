import { apiClient } from './apiClient'

export interface ManagedDriver {
  id: string
  full_name: string
  username: string
  email: string
  phone?: string
  is_active: boolean
  device_enrollment_status: 'pending' | 'enrolled' | 'revoked'
  device?: { device_model?: string; enrolled_at?: string; last_seen_at?: string } | null
  active_route?: { id: string; route_code?: string } | null
  assigned_vehicle?: { id: string; registration_number?: string } | null
}

export interface CreateDriverPayload {
  full_name: string
  username: string
  email: string
  phone?: string
  temporary_password: string
  is_active: boolean
}

export const driverAdminService = {
  list: () => apiClient.get<ManagedDriver[]>('/users/drivers/manage'),
  listAssignable: () => apiClient.get<ManagedDriver[]>('/users/drivers/list'),
  create: (payload: CreateDriverPayload) => apiClient.post<ManagedDriver>('/users/drivers', payload),
  update: (id: string, payload: Partial<Pick<CreateDriverPayload, 'full_name' | 'username' | 'email' | 'phone'>>) =>
    apiClient.put<ManagedDriver>(`/users/drivers/${id}`, payload),
  resetDevice: (id: string, temporaryPassword: string) =>
    apiClient.post<ManagedDriver>(`/users/drivers/${id}/reset-device`, { temporary_password: temporaryPassword }),
  setActive: (id: string, active: boolean) =>
    apiClient.patch<ManagedDriver>(`/users/drivers/${id}/${active ? 'activate' : 'deactivate'}`),
}
