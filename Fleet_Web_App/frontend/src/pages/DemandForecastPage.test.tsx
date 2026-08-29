import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { forecastService } from '../services/forecastService'
import { DemandForecastPage, OperationalContext } from './DemandForecastPage'

vi.mock('../utils/download', () => ({ saveDownload: vi.fn() }))
vi.mock('../services/authService', () => ({ authService: { getSession: () => ({ role: 'fleet_manager', permissions: ['demand.refresh', 'reports.export'] }) } }))

vi.mock('../services/forecastService', () => ({
  forecastService: {
    getModelStatus: vi.fn(),
    getDashboardSummary: vi.fn(),
    getForecastVsActual: vi.fn(),
    getOperationalZones: vi.fn(),
    getOperationalContext: vi.fn(),
    listForecastRuns: vi.fn(),
    getForecastRun: vi.fn(),
    generateForecast: vi.fn(),
    exportForecast: vi.fn(),
  },
}))

const activeRun = {
  model_run_id: 'run-approved-30', model_version: 'demand-v2.1',
  forecast_start_date: '2026-08-28T00:00:00+00:00', forecast_end_date: '2026-09-26T00:00:00+00:00', horizon_days: 30,
  records_generated: 90, zones_count: 3, source_requested: 'model', run_type: 'controlled',
  effective_source: 'model', fallback_used: false,
  activated_at: '2026-08-28T08:30:00Z', request_fingerprint: 'forecast-30-model',
  planning_window: {
    basis: 'colombo_business_date', dataset_end_date: '2026-04-01',
    forecast_start_date: '2026-08-28T00:00:00+00:00', forecast_end_date: '2026-09-26T00:00:00+00:00',
    horizon_days: 30,
  },
}

const forecastDates = ['2026-08-28', '2026-08-29', '2026-08-30', '2026-08-31', '2026-09-01', '2026-09-02', '2026-09-03', '2026-09-04']
const forecasts = Array.from({ length: 8 }, (_, index) => ({
  zoneId: 'LK_colombo_central', zone: 'Colombo Central',
  date: forecastDates[index],
  currentVolume: 0, actualAvailable: false, predictedVolume: 20 + index, variance: 0,
  varianceOrders: null, action: 'Review capacity', demandLevel: 'medium' as const,
  requiredVehicles: 2, lowerBound: 15, upperBound: 30,
}))

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  vi.mocked(forecastService.getModelStatus).mockResolvedValue({ operational_state: 'ready', active_run: activeRun })
  vi.mocked(forecastService.getDashboardSummary).mockResolvedValue({ high_demand_zones: 1, very_high_demand_zones: 0, total_predicted_demand_next_7_days: 161, total_required_vehicles_next_7_days: 14 })
  vi.mocked(forecastService.getForecastVsActual).mockResolvedValue(forecasts)
  vi.mocked(forecastService.getOperationalZones).mockResolvedValue([{ id: 'LK_colombo_central', name: 'Colombo Central', latitude: 6.9271, longitude: 79.8612, serviceRadiusKm: 12 }])
  vi.mocked(forecastService.getOperationalContext).mockResolvedValue({ date: '2026-08-28', holiday_name: null, is_holiday: false, rain_probability: 35, weather_label: 'Cloudy', artifact_source: 'Colombo zone demand forecast', last_refresh_at: null })
  vi.mocked(forecastService.listForecastRuns).mockResolvedValue([activeRun])
  vi.mocked(forecastService.getForecastRun).mockResolvedValue({ run: activeRun, items: forecasts, total: forecasts.length })
  vi.mocked(forecastService.generateForecast).mockResolvedValue({ reused_active_run: true, active_run: activeRun })
  vi.mocked(forecastService.exportForecast).mockResolvedValue({ blob: new Blob(['csv']), filename: 'demand.csv' })
})

afterEach(cleanup)

describe('DemandForecastPage controls', () => {
  it('changes the display horizon without generating a forecast', async () => {
    render(<DemandForecastPage />)
    await screen.findByRole('heading', { name: 'Zone Demand Forecast' })

    fireEvent.click(screen.getByRole('radio', { name: '7 days' }))

    expect(forecastService.generateForecast).not.toHaveBeenCalled()
    expect(screen.getByText('Showing 7 forecast days')).toBeInTheDocument()
    expect(screen.getAllByText('2026-08-28 to 2026-09-03')).toHaveLength(2)
    expect(screen.getByText('7 forecast rows')).toBeInTheDocument()
    expect(screen.getByText('7-day Demand Trend')).toBeInTheDocument()
    expect(screen.getByText('7-day Forecast Details')).toBeInTheDocument()
    expect(screen.getByText('2026-09-03')).toBeInTheDocument()
    expect(screen.queryByText('2026-09-04')).not.toBeInTheDocument()
  })

  it('refreshes current API data without generating a forecast', async () => {
    render(<DemandForecastPage />)
    await screen.findByRole('heading', { name: 'Zone Demand Forecast' })
    expect(forecastService.getModelStatus).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: 'Refresh View' }))

    await waitFor(() => expect(forecastService.getModelStatus).toHaveBeenCalledTimes(2))
    expect(forecastService.generateForecast).not.toHaveBeenCalled()
    expect(await screen.findByRole('status')).toHaveTextContent('Forecast view refreshed from current API data.')
  })

  it('confirms generation and sends the selected horizon', async () => {
    render(<DemandForecastPage />)
    await screen.findByRole('heading', { name: 'Zone Demand Forecast' })
    fireEvent.click(screen.getByRole('radio', { name: '14 days' }))

    fireEvent.click(screen.getByRole('button', { name: 'Generate Forecast' }))
    const dialog = screen.getByRole('dialog', { name: 'Generate forecast' })
    expect(forecastService.generateForecast).not.toHaveBeenCalled()

    fireEvent.click(within(dialog).getByRole('button', { name: 'Generate Forecast' }))

    await waitFor(() => expect(forecastService.generateForecast).toHaveBeenCalledWith(14))
  })

  it('shows approved active-run metadata using operational wording', async () => {
    render(<DemandForecastPage />)

    expect(await screen.findByText('Active Forecast')).toBeInTheDocument()
    expect(screen.queryByText('Forecast model version')).not.toBeInTheDocument()
    expect(screen.queryByText('demand-v2.1')).not.toBeInTheDocument()
    expect(screen.getByText('Approved planning window')).toBeInTheDocument()
    const activePanel = screen.getByText('Approved planning window').closest('section')
    expect(activePanel).not.toBeNull()
    expect(within(activePanel as HTMLElement).getByText('2026-08-28 to 2026-09-26')).toBeInTheDocument()
    expect(screen.getByText('This planning window was fixed when the cycle was generated. Refresh View reloads saved data without changing forecast values.')).toBeInTheDocument()
    expect(screen.getByText('90 records across 3 zones')).toBeInTheDocument()
    expect(screen.getByText('Approved forecast engine')).toBeInTheDocument()
    expect(screen.queryByText(/synthetic/i)).not.toBeInTheDocument()
  })

  it('reports reused approved-run feedback deterministically after generation', async () => {
    render(<DemandForecastPage />)
    await screen.findByRole('heading', { name: 'Zone Demand Forecast' })
    fireEvent.click(screen.getByRole('button', { name: 'Generate Forecast' }))
    fireEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Generate Forecast' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Approved forecast run reused for the 30-day horizon.')
    expect(screen.getByText('Reused approved run')).toBeInTheDocument()
  })

  it('exports only the currently displayed forecast horizon', async () => {
    render(<DemandForecastPage />)
    await screen.findByRole('heading', { name: 'Zone Demand Forecast' })
    fireEvent.click(screen.getByRole('radio', { name: '7 days' }))

    fireEvent.click(screen.getByRole('button', { name: 'Export Forecast' }))

    await waitFor(() => expect(forecastService.exportForecast).toHaveBeenCalledWith({
      zone_id: undefined,
      start_date: '2026-08-28',
      end_date: '2026-09-03',
    }))
  })

  it('opens forecast history and loads the selected saved run from the database', async () => {
    render(<DemandForecastPage />)
    await screen.findByRole('heading', { name: 'Zone Demand Forecast' })

    fireEvent.click(screen.getByRole('button', { name: 'Forecast History' }))
    const historyDialog = screen.getByRole('dialog', { name: 'Forecast history' })
    fireEvent.click(within(historyDialog).getByRole('button', { name: /2026-08-28 to 2026-09-26/i }))

    await waitFor(() => expect(forecastService.getForecastRun).toHaveBeenCalledWith('run-approved-30'))
    expect(within(historyDialog).getAllByText('Colombo Central')).toHaveLength(8)
    expect(within(historyDialog).getByText('20')).toBeInTheDocument()
    expect(within(historyDialog).getByText('Saved forecast records')).toBeInTheDocument()
  })
})

describe('OperationalContext', () => {
  it('shows honest operational context without unsupported scenario controls', () => {
    render(<OperationalContext context={{ date: '2027-01-01', holiday_name: null, is_holiday: false, rain_probability: 35, weather_label: 'Cloudy', artifact_source: 'Colombo zone demand forecast', last_refresh_at: null }} />)

    expect(screen.getByText('Operational Context')).toBeInTheDocument()
    expect(screen.queryByText('Rain probability')).not.toBeInTheDocument()
    expect(screen.queryByText('35%')).not.toBeInTheDocument()
    expect(screen.queryByText('Promotion')).not.toBeInTheDocument()
    expect(screen.queryByText('Manual Demand Spike (%)')).not.toBeInTheDocument()
  })
})
