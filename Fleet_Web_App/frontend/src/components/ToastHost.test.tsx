import { act, fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { showToast } from '../utils/toast'
import { ToastHost } from './ToastHost'

describe('ToastHost', () => {
  it('shows and dismisses operational feedback', () => {
    render(<ToastHost />)
    act(() => showToast({ tone: 'success', title: 'Part deleted', message: 'History is preserved.' }))

    expect(screen.getByText('Part deleted')).toBeInTheDocument()
    expect(screen.getByText('History is preserved.')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss notification' }))
    expect(screen.queryByText('Part deleted')).not.toBeInTheDocument()
  })
})
