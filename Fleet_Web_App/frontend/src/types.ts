export type UserRole = 'admin' | 'fleet_manager' | 'planner' | 'maintenance_staff'

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export type ModelStatus = 'Placeholder baseline' | 'Placeholder moving average' | 'Unavailable'

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  organization: string
}

export interface Vehicle {
  id: string
  number: string
  model: string
  type: string
  assignedDriver: string
  mileage: number
  status: 'Active' | 'Maintenance' | 'In Transit' | 'Offline'
  risk: RiskLevel
  route?: string
}

export interface VehiclePart {
  id: string
  vehicleId: string
  name: string
  lastService: string
  failures: number
  risk: RiskLevel
  predictedNext: string
  note: string
}

export interface MaintenanceRecord {
  id: string
  date: string
  vehicle: string
  service: string
  technician: string
  cost: string
  status: 'Completed' | 'Pending Parts' | 'Overdue'
}

export interface DeliveryOrder {
  id: string
  customer: string
  priority: 'Critical' | 'High' | 'Standard'
  timeWindow: string
  zone: string
  location: string
  status: 'Unassigned' | 'Routed' | 'In Transit'
}

export interface RouteStop {
  sequence: number
  name: string
  eta: string
  loadDrop: string
  status: 'Origin' | 'Pending' | 'Complete'
}

export interface RoutePlan {
  id: string
  vehicle: string
  driver: string
  distance: string
  eta: string
  capacityUse: number
  stops: RouteStop[]
  warning: string
}

export interface TripEvent {
  id: string
  time: string
  title: string
  description: string
  severity: 'info' | 'warning' | 'critical'
}

export interface Alert {
  id: string
  time: string
  title: string
  description: string
  severity: 'critical' | 'warning' | 'info'
  category: 'maintenance' | 'route' | 'demand' | 'driver'
  vehicle?: string
  acknowledged: boolean
}

export interface DemandZone {
  id: string
  name: string
  predicted: number
  actual: number
  overloadScore: number
  risk: RiskLevel
}

export interface DemandForecast {
  zone: string
  currentVolume: number
  predictedVolume: number
  variance: number
  action: string
}
