import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetService } from '../services/fleetService'
import type { MaintenanceRecord, Vehicle } from '../types'
import { MaintenanceHistoryPage } from './MaintenanceHistoryPage'

vi.mock('../services/fleetService', () => ({ fleetService: { listMaintenanceRecords: vi.fn(), listVehicles: vi.fn() } }))
const vehicles = [{ id: 'v1', registrationNumber: 'WP CAA-1208', vehicleCode: 'QA-EV-008' }, { id: 'v2', registrationNumber: 'WP CAB-9001', vehicleCode: 'QA-VAN-009' }] as Vehicle[]
const base = { date: 'Aug 27, 2026', partName: 'General', maintenanceType: 'corrective', priority: 'medium', service: 'Service', technician: 'Engineer', cost: 'LKR 1,000', costValue: 1000, status: 'Completed', workOrderStatus: 'completed', eventKind: 'corrective_repair', issueType: 'Completed repair', serviceDate: '2026-08-27T08:00:00Z', createdAt: '2026-08-26T08:00:00Z' } as const
const records = [{ ...base, id: 'r1', vehicleId: 'v1', vehicle: 'WP CAA-1208' }, { ...base, id: 'r2', vehicleId: 'v2', vehicle: 'WP CAB-9001', eventKind: 'inspection', issueType: 'Safety inspection' }] as MaintenanceRecord[]
beforeEach(() => { vi.clearAllMocks(); vi.mocked(fleetService.listVehicles).mockResolvedValue(vehicles); vi.mocked(fleetService.listMaintenanceRecords).mockResolvedValue(records) })

describe('MaintenanceHistoryPage', () => {
  it('filters by vehicle identity and record type and exposes no lifecycle controls', async () => {
    render(<MemoryRouter><MaintenanceHistoryPage /></MemoryRouter>)
    expect(await screen.findByText('Completed repair')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Search maintenance history'), { target: { value: 'QA-VAN-009' } })
    expect(screen.queryByText('Completed repair')).not.toBeInTheDocument()
    expect(screen.getByText('Safety inspection')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Record type'), { target: { value: 'corrective_repair' } })
    expect(screen.getByText('No matching maintenance history')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Start Work' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Complete Work' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cancel Work' })).not.toBeInTheDocument()
  })
})
