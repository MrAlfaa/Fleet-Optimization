import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { OperationalContext } from './DemandForecastPage'

describe('OperationalContext', () => {
  it('shows honest operational context without unsupported scenario controls', () => {
    render(<OperationalContext context={{ date: '2026-08-16', holiday_name: null, is_holiday: false, rain_probability: 35, weather_label: 'Cloudy', artifact_source: 'Olist artifact', last_refresh_at: null }} />)

    expect(screen.getByText('Operational Context')).toBeInTheDocument()
    expect(screen.getByText('35%')).toBeInTheDocument()
    expect(screen.queryByText('Promotion')).not.toBeInTheDocument()
    expect(screen.queryByText('Manual Demand Spike (%)')).not.toBeInTheDocument()
  })
})
