import { apiClient } from './apiClient'

export type LicenseState = 'disabled' | 'active' | 'expired' | 'invalid_configuration'

export interface LicenseStatus {
  enabled: boolean
  status: LicenseState
  blocked: boolean
  customerName: string
  expiresAt: string | null
  supportMessage: string
}

interface BackendLicenseStatus {
  enabled: boolean
  status: LicenseState
  blocked: boolean
  customer_name: string
  expires_at: string | null
  support_message: string
}

export const licenseService = {
  async getStatus(): Promise<LicenseStatus> {
    const status = await apiClient.get<BackendLicenseStatus>('/health/license', { skipAuth: true })
    return {
      enabled: status.enabled,
      status: status.status,
      blocked: status.blocked,
      customerName: status.customer_name,
      expiresAt: status.expires_at,
      supportMessage: status.support_message,
    }
  },
}
