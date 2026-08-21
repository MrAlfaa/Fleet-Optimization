import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LoadingState, OperationalInfo } from './UI'

describe('LoadingState', () => {
  it('renders an accessible animated skeleton', () => {
    render(<LoadingState label="Loading demand forecast" />)

    expect(screen.getByRole('status', { name: 'Loading demand forecast' })).toBeInTheDocument()
    expect(screen.getByText('Loading demand forecast')).toHaveClass('sr-only')
    expect(screen.getByTestId('loading-skeleton')).toHaveClass('animate-pulse', 'motion-reduce:animate-none')
  })
})

describe('OperationalInfo', () => {
  it('reveals contextual guidance on demand and closes with Escape', () => {
    render(<OperationalInfo title="Model guidance">Use this output cautiously.</OperationalInfo>)

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Model guidance' }))
    expect(screen.getByRole('dialog', { name: 'Model guidance' })).toHaveTextContent('Use this output cautiously.')
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
