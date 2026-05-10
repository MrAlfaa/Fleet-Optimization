import { maintenanceRecords, vehicleParts, vehicles } from '../data/mockData'

export const fleetService = {
  listVehicles: () => Promise.resolve(vehicles),
  getVehicle: (vehicleId: string) =>
    Promise.resolve(vehicles.find((vehicle) => vehicle.id === vehicleId) ?? vehicles[0]),
  listVehicleParts: (vehicleId: string) =>
    Promise.resolve(vehicleParts.filter((part) => part.vehicleId === vehicleId)),
  listMaintenanceRecords: () => Promise.resolve(maintenanceRecords),
}
