export interface EvPartCatalogItem {
  key: string
  name: string
  category: string
  description: string
  mlSupported: boolean
  mlSignalGroup: string | null
}

export interface ExistingPartSummary {
  id?: string
  name: string
  isActive?: boolean
}

export type PartAvailability = 'available' | 'active' | 'archived'

export function buildPartOptions(catalog: EvPartCatalogItem[], parts: ExistingPartSummary[]) {
  return catalog.map((item) => {
    const existing = parts.find((part) => part.name.localeCompare(item.name, undefined, { sensitivity: 'accent' }) === 0)
    return {
      ...item,
      availability: existing ? (existing.isActive === false ? 'archived' : 'active') as PartAvailability : 'available' as PartAvailability,
      existingPartId: existing?.id,
    }
  })
}
