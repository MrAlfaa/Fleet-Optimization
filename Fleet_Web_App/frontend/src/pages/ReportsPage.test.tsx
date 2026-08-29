import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetService } from '../services/fleetService'
import { reportService } from '../services/reportService'
import type { Vehicle } from '../types'
import { saveDownload } from '../utils/download'
import { ReportsPage } from './ReportsPage'

vi.mock('../services/fleetService', () => ({ fleetService: { listVehicles: vi.fn() } }))
vi.mock('../services/reportService', () => ({ reportService: { export: vi.fn() } }))
vi.mock('../utils/download', () => ({ saveDownload: vi.fn() }))
vi.mock('../services/authService', () => ({ authService: { getSession: () => ({ role: 'fleet_manager', permissions: ['reports.export'] }) } }))

const vehicle = { id: 'vehicle-1', registrationNumber: 'WP CAA-1208', vehicleCode: 'QA-EV-008' } as Vehicle

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  vi.mocked(fleetService.listVehicles).mockResolvedValue([vehicle])
  vi.mocked(reportService.export).mockResolvedValue({ blob: new Blob(['report']), filename: 'vehicle-maintenance.xlsx' })
})

afterEach(cleanup)

describe('ReportsPage', () => {
  it('uses business terminology and reveals only filters applicable to the selected report', async () => {
    const { container } = render(<ReportsPage />)
    expect(await screen.findByRole('option', { name: 'WP CAA-1208 · QA-EV-008' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Reports' })).toBeInTheDocument()
    expect(screen.getByLabelText('Assessment result')).toBeInTheDocument()
    expect(screen.getByLabelText('Workflow status')).toBeInTheDocument()
    expect(screen.getByLabelText('Inspection status')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('radio', { name: /Vehicle Details Report/i }))
    expect(screen.queryByLabelText('Assessment result')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Workflow status')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Inspection status')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('radio', { name: /Daily Inspection Report/i }))
    expect(screen.getByLabelText('Inspection status')).toBeInTheDocument()
    expect(screen.queryByLabelText('Assessment result')).not.toBeInTheDocument()
    expect(container.textContent).not.toMatch(/\b(ML|model|prediction|synthetic|threshold|artifact)\b/i)
  })

  it('submits only the selected report filters and downloads the returned file', async () => {
    render(<ReportsPage />)
    await screen.findByRole('option', { name: 'WP CAA-1208 · QA-EV-008' })
    fireEvent.change(screen.getByLabelText('Vehicle'), { target: { value: 'vehicle-1' } })
    fireEvent.change(screen.getByLabelText('Vehicle category'), { target: { value: 'bus' } })
    fireEvent.change(screen.getByLabelText('Start date'), { target: { value: '2026-08-01' } })
    fireEvent.change(screen.getByLabelText('End date'), { target: { value: '2026-08-27' } })
    fireEvent.change(screen.getByLabelText('Assessment result'), { target: { value: 'high' } })
    fireEvent.change(screen.getByLabelText('Workflow status'), { target: { value: 'inspection' } })
    fireEvent.change(screen.getByLabelText('Inspection status'), { target: { value: 'assigned' } })
    fireEvent.click(screen.getByRole('button', { name: 'Generate Excel' }))

    await waitFor(() => expect(reportService.export).toHaveBeenCalledWith({
      format: 'xlsx',
      report_type: 'vehicle_maintenance',
      vehicle_id: 'vehicle-1',
      vehicle_category: 'bus',
      start_date: '2026-08-01',
      end_date: '2026-08-27',
      assessment_result: 'high',
      workflow_status: 'inspection',
      inspection_status: 'assigned',
    }))
    expect(saveDownload).toHaveBeenCalled()
    expect(await screen.findByText('vehicle-maintenance.xlsx is ready.')).toBeInTheDocument()
  })

  it('prevents duplicate generation while a report is in progress', async () => {
    let resolveExport!: (value: { blob: Blob; filename: string }) => void
    vi.mocked(reportService.export).mockReturnValue(new Promise((resolve) => { resolveExport = resolve }))
    render(<ReportsPage />)
    await screen.findByRole('option', { name: 'WP CAA-1208 · QA-EV-008' })
    fireEvent.click(screen.getByRole('button', { name: 'Generate Excel' }))
    const progress = screen.getByRole('button', { name: 'Generating Excel...' })
    expect(progress).toBeDisabled()
    fireEvent.click(progress)
    expect(reportService.export).toHaveBeenCalledTimes(1)
    resolveExport({ blob: new Blob(), filename: 'report.xlsx' })
    expect(await screen.findByText('report.xlsx is ready.')).toBeInTheDocument()
  })

  it('validates date ordering and shows report generation failures', async () => {
    render(<ReportsPage />)
    await screen.findByRole('option', { name: 'WP CAA-1208 · QA-EV-008' })
    fireEvent.change(screen.getByLabelText('Start date'), { target: { value: '2026-08-27' } })
    fireEvent.change(screen.getByLabelText('End date'), { target: { value: '2026-08-01' } })
    expect(screen.getByText('Start date must be on or before the end date.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Generate Excel' })).toBeDisabled()

    fireEvent.change(screen.getByLabelText('End date'), { target: { value: '2026-08-28' } })
    vi.mocked(reportService.export).mockRejectedValueOnce(new Error('Report service unavailable'))
    fireEvent.click(screen.getByRole('button', { name: 'Generate Excel' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Report service unavailable')
  })

  it('offers demand and route reports with only relevant planning filters', async () => {
    render(<ReportsPage />)
    await screen.findByRole('option', { name: 'WP CAA-1208 · QA-EV-008' })

    fireEvent.click(screen.getByRole('radio', { name: /Zone Demand Forecast Report/i }))
    expect(screen.getByLabelText('Operational zone')).toBeInTheDocument()
    expect(screen.getByLabelText('Demand level')).toBeInTheDocument()
    expect(screen.queryByLabelText('Vehicle')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('radio', { name: /Route Optimization Report/i }))
    expect(screen.getByLabelText('Vehicle')).toBeInTheDocument()
    expect(screen.getByLabelText('Route status')).toBeInTheDocument()
    expect(screen.getByLabelText('Delivery period')).toBeInTheDocument()
    expect(screen.queryByLabelText('Demand level')).not.toBeInTheDocument()
  })

  it('submits route planning filters without maintenance-only values', async () => {
    render(<ReportsPage />)
    await screen.findByRole('option', { name: 'WP CAA-1208 · QA-EV-008' })
    fireEvent.click(screen.getByRole('radio', { name: /Route Stop Status Report/i }))
    fireEvent.change(screen.getByLabelText('Vehicle'), { target: { value: 'vehicle-1' } })
    fireEvent.change(screen.getByLabelText('Route status'), { target: { value: 'completed' } })
    fireEvent.change(screen.getByLabelText('Delivery period'), { target: { value: 'second_half' } })
    fireEvent.click(screen.getByRole('button', { name: 'Generate Excel' }))

    await waitFor(() => expect(reportService.export).toHaveBeenCalledWith({
      format: 'xlsx',
      report_type: 'route_stop_performance',
      vehicle_id: 'vehicle-1',
      route_status: 'completed',
      delivery_period: 'second_half',
    }))
  })

  it('offers consolidation, driver, and route detail reports with their own filters', async () => {
    render(<ReportsPage />)
    await screen.findByRole('option', { name: 'WP CAA-1208 · QA-EV-008' })

    fireEvent.click(screen.getByRole('radio', { name: /Parcel Consolidation Report/i }))
    expect(screen.getByLabelText('Consolidation ID')).toBeInTheDocument()
    expect(screen.getByLabelText('Consolidation status')).toBeInTheDocument()
    expect(screen.getByLabelText('Delivery period')).toBeInTheDocument()
    expect(screen.queryByLabelText('Vehicle')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('radio', { name: /Driver Details Report/i }))
    expect(screen.getByLabelText('Driver account status')).toBeInTheDocument()
    expect(screen.getByLabelText('Device enrollment')).toBeInTheDocument()
    expect(screen.queryByLabelText('Consolidation status')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('radio', { name: /Route Details Report/i }))
    expect(screen.getByLabelText('Vehicle')).toBeInTheDocument()
    expect(screen.getByLabelText('Consolidation ID')).toBeInTheDocument()
    expect(screen.getByLabelText('Route status')).toBeInTheDocument()
  })

  it('exports the consolidation report with exact operational filters', async () => {
    render(<ReportsPage />)
    await screen.findByRole('option', { name: 'WP CAA-1208 · QA-EV-008' })
    fireEvent.click(screen.getByRole('radio', { name: /Parcel Consolidation Report/i }))
    fireEvent.change(screen.getByLabelText('Consolidation ID'), { target: { value: 'PCID202608291H001' } })
    fireEvent.change(screen.getByLabelText('Consolidation status'), { target: { value: 'routed' } })
    fireEvent.change(screen.getByLabelText('Delivery period'), { target: { value: 'first_half' } })
    fireEvent.click(screen.getByRole('button', { name: 'Generate Excel' }))

    await waitFor(() => expect(reportService.export).toHaveBeenCalledWith({
      format: 'xlsx',
      report_type: 'consolidation_details',
      consolidation_id: 'PCID202608291H001',
      consolidation_status: 'routed',
      delivery_period: 'first_half',
    }))
  })
})
