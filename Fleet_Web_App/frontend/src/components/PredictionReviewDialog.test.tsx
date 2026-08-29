import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { MaintenanceReview } from '../types'
import { PredictionReviewDialog } from './PredictionReviewDialog'

const review: MaintenanceReview = {
  id: 'review-1', vehicleId: 'vehicle-1', vehicleRegistration: 'WP CAA-1234', vehicleCode: 'FLEET-1',
  predictionId: 'prediction-1', featureHash: 'hash-1', risk: 'critical', status: 'pending', notes: '',
  createdAt: '2026-08-24T06:30:00Z', updatedAt: '2026-08-24T06:30:00Z', resolvedAt: null, resolvedBy: '',
}

describe('PredictionReviewDialog', () => {
  it('requires inspection evidence before a resolution can be submitted', () => {
    render(<PredictionReviewDialog onClose={vi.fn()} onResolved={vi.fn()} review={review} />)
    fireEvent.click(screen.getByRole('button', { name: 'Clear vehicle' }))
    expect(screen.getByRole('alert')).toHaveTextContent('at least 10 characters')
  })

  it('explains that confirming an issue keeps the dispatch hold', () => {
    render(<PredictionReviewDialog onClose={vi.fn()} onResolved={vi.fn()} review={review} />)
    expect(screen.getAllByText(/keep the hold until linked maintenance is completed/i).length).toBeGreaterThan(0)
  })
})
