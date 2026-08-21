import { apiClient } from './apiClient'

export interface SearchResult {
  type: string
  id: string
  title: string
  subtitle: string
  path: string
}

export const searchService = {
  async search(query: string): Promise<SearchResult[]> {
    const data = await apiClient.get<{ items: SearchResult[] }>('/search', { query: { q: query } })
    return data.items
  },
}
