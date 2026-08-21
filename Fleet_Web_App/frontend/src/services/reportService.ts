import { apiClient } from './apiClient'

export const reportService = {
  export(format: 'pdf' | 'xlsx', start_date?: string, end_date?: string) {
    return apiClient.download('/reports/export', { query: { format, start_date, end_date } })
  },
}
