import type { MaintenanceRecord, Vehicle } from '../../types'

export interface VehicleMaintenanceSummary {
  vehicle: Vehicle
  total: number
  open: number
  overdue: number
  completed: number
  outstandingCost: number
  latestRecord: MaintenanceRecord | null
}

export function summarizeMaintenanceByVehicle(vehicles: Vehicle[], records: MaintenanceRecord[]): VehicleMaintenanceSummary[] {
  return vehicles.map((vehicle) => {
    const related = records.filter((record) => record.vehicleId === vehicle.id)
    const open = related.filter((record) => record.status !== 'Completed')
    return {
      vehicle,
      total: related.length,
      open: open.length,
      overdue: related.filter((record) => record.status === 'Overdue').length,
      completed: related.filter((record) => record.status === 'Completed').length,
      outstandingCost: open.reduce((total, record) => total + record.costValue, 0),
      latestRecord: related[0] ?? null,
    }
  }).sort((a, b) => b.overdue - a.overdue || b.open - a.open || a.vehicle.registrationNumber.localeCompare(b.vehicle.registrationNumber))
}
