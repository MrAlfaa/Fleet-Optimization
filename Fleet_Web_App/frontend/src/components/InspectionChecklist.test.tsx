import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { InspectionChecklist } from './InspectionChecklist'
import { validateInspectionChecklist, type InspectionChecklistFormItem } from '../features/maintenance/inspectionChecklist'

const items: InspectionChecklistFormItem[] = [
  { key: 'braking', label: 'Braking', outcome: null, remark: '' },
]

afterEach(cleanup)

describe('InspectionChecklist', () => {
  it('requires a remark when an issue is found', () => {
    const errors = validateInspectionChecklist([{ ...items[0], outcome: 'failed' }], true)
    expect(errors.braking).toMatch(/remark/i)
  })

  it('requires every item before final completion', () => {
    const errors = validateInspectionChecklist(items, true)
    expect(errors.braking).toMatch(/select/i)
  })

  it('uses accessible controlled outcomes', () => {
    const onChange = vi.fn()
    render(<InspectionChecklist items={items} onChange={onChange} />)
    fireEvent.click(screen.getByRole('radio', { name: 'Issue found' }))
    expect(onChange).toHaveBeenCalledWith([{ ...items[0], outcome: 'failed' }])
  })

  it('renders immutable evidence without editable controls', () => {
    render(<InspectionChecklist items={[{ ...items[0], outcome: 'passed' }]} onChange={vi.fn()} readOnly />)
    expect(screen.getByText('Passed')).toBeInTheDocument()
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
  })
})
