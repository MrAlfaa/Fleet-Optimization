import type { InspectionPriority, MaintenanceSystem } from '../../types'

export const maintenanceSystemOptions: Array<{ value: MaintenanceSystem; label: string }> = [
  { value: 'battery_system', label: 'Battery system' },
  { value: 'braking', label: 'Braking' },
  { value: 'charging_system', label: 'Charging system' },
  { value: 'cooling_system', label: 'Cooling system' },
  { value: 'electrical', label: 'Electrical' },
  { value: 'engine', label: 'Engine' },
  { value: 'exhaust_dpf', label: 'Exhaust and DPF' },
  { value: 'fuel_system', label: 'Fuel system' },
  { value: 'ignition', label: 'Ignition' },
  { value: 'motor_drivetrain', label: 'Motor and drivetrain' },
  { value: 'steering', label: 'Steering' },
  { value: 'suspension', label: 'Suspension' },
  { value: 'thermal_system', label: 'Thermal system' },
  { value: 'tires', label: 'Tires' },
]

export const maintenancePriorityOptions: InspectionPriority[] = ['low', 'medium', 'high', 'critical']
