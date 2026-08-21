import { describe, expect, it } from 'vitest'
import { summarizeMaintenanceByVehicle } from './maintenanceSummary'
import type { MaintenanceRecord, Vehicle } from '../../types'

const vehicle = (id: string): Vehicle => ({ id, number: id, registrationNumber: id, vehicleCode: id, imageUrl: null, category: 'Electric Van', model: 'BYD eVan', type: 'electric_van', assignedDriver: 'Unassigned', mileage: 0, status: 'Active', risk: 'low' })
const record = (vehicleId: string, status: MaintenanceRecord['status'], costValue = 0): MaintenanceRecord => ({ id: `${vehicleId}-${status}`, vehicleId, date: 'Aug 16, 2026', vehicle: vehicleId, partName: 'Battery Pack', maintenanceType: 'inspection', priority: 'medium', service: 'Battery inspection', technician: 'QA', cost: `$${costValue}`, costValue, status })

describe('summarizeMaintenanceByVehicle', () => {
  it('keeps vehicles without records and prioritizes overdue vehicles', () => {
    const result = summarizeMaintenanceByVehicle([vehicle('WP-1'), vehicle('WP-2')], [record('WP-2', 'Overdue', 500), record('WP-2', 'Completed', 100)])
    expect(result[0]).toMatchObject({ open: 1, overdue: 1, completed: 1, outstandingCost: 500 })
    expect(result[1]).toMatchObject({ total: 0, open: 0 })
  })
})
