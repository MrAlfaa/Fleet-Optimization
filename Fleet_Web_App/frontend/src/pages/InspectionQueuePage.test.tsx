import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetService } from '../services/fleetService'
import type { Vehicle, VehicleMaintenanceInspection } from '../types'
import { InspectionQueuePage } from './InspectionQueuePage'

vi.mock('../services/fleetService', () => ({ fleetService: { listInspections: vi.fn(), listVehicles: vi.fn(), listInspectionAssignees: vi.fn(), assignInspection: vi.fn(), cancelInspection: vi.fn() } }))
vi.mock('../services/authService', () => ({ authService: { getSession: () => ({ role: 'fleet_manager' }) } }))

const vehicles = [
  { id: 'vehicle-1', registrationNumber: 'WP CAA-1208', vehicleCode: 'QA-EV-008', model: 'BYD T3' },
  { id: 'vehicle-2', registrationNumber: 'WP CAB-4500', vehicleCode: 'QA-VAN-002', model: 'Nissan NV200' },
] as Vehicle[]
const inspections = [
  { id: 'inspection-1', vehicleId: 'vehicle-1', status: 'pending', priority: 'high', inspectionAreas: ['Braking'], assignedTo: null, createdAt: '2026-08-27T08:00:00Z', isActive: true },
  { id: 'inspection-2', vehicleId: 'vehicle-2', status: 'assigned', priority: 'medium', inspectionAreas: ['Tires'], assignedTo: 'user-1', createdAt: '2026-08-27T09:00:00Z', isActive: true },
  { id: 'inspection-3', vehicleId: 'vehicle-1', status: 'decision_pending', priority: 'high', inspectionAreas: ['Braking'], assignedTo: 'user-1', createdAt: '2026-08-27T10:00:00Z', isActive: true },
] as VehicleMaintenanceInspection[]

beforeEach(() => {
  vi.mocked(fleetService.listVehicles).mockResolvedValue(vehicles)
  vi.mocked(fleetService.listInspectionAssignees).mockResolvedValue([{ id: 'user-1', fullName: 'M. Perera', role: 'maintenance_manager' }])
  vi.mocked(fleetService.listInspections).mockResolvedValue({ items: inspections, page: 1, limit: 100, total: 3, pages: 1 })
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

describe('InspectionQueuePage', () => {
  it('filters by vehicle identity and keeps fleet managers read-only', async () => {
    render(<MemoryRouter><InspectionQueuePage /></MemoryRouter>)
    expect((await screen.findAllByText('WP CAA-1208')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('WP CAB-4500').length).toBeGreaterThan(0)
    fireEvent.change(screen.getByLabelText('Search inspection vehicles'), { target: { value: 'QA-EV-008' } })
    expect(screen.getAllByText('WP CAA-1208').length).toBeGreaterThan(0)
    expect(screen.queryAllByText('WP CAB-4500')).toHaveLength(0)
    expect(screen.queryByRole('button', { name: 'Assign inspection' })).not.toBeInTheDocument()
  })

  it('shows a useful empty state when filters have no match', async () => {
    render(<MemoryRouter><InspectionQueuePage /></MemoryRouter>)
    await screen.findAllByText('WP CAA-1208')
    fireEvent.change(screen.getByLabelText('Inspection priority filter'), { target: { value: 'critical' } })
    expect(screen.getByText('No matching inspections')).toBeInTheDocument()
  })

  it('routes assigned work to inspection and pending decisions to outcome review', async () => {
    render(<MemoryRouter><InspectionQueuePage /></MemoryRouter>)
    await screen.findAllByText('WP CAA-1208')
    expect(screen.getAllByRole('link', { name: 'Open Inspection' })[0]).toHaveAttribute('href', '/maintenance/inspections/inspection-2')
    expect(screen.getAllByRole('link', { name: 'Review Outcome' })[0]).toHaveAttribute('href', '/maintenance/inspections/inspection-3/decision')
  })
})
