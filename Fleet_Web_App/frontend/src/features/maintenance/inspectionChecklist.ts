import type { InspectionCheckOutcome } from '../../types'

export interface InspectionChecklistFormItem {
  key: string
  label: string
  outcome: InspectionCheckOutcome | null
  remark: string
}

export function validateInspectionChecklist(items: InspectionChecklistFormItem[], requireAll: boolean) {
  return items.reduce<Record<string, string>>((errors, item) => {
    if (requireAll && !item.outcome) errors[item.key] = 'Select an inspection outcome.'
    else if (item.outcome === 'failed' && !item.remark.trim()) errors[item.key] = 'Add a remark for the issue found.'
    return errors
  }, {})
}
