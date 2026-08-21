export type UserRole = 'admin' | 'fleet_manager' | 'maintenance_manager' | 'route_planner' | 'driver'

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export type ModelStatus = 'Available' | 'Loaded' | 'Unavailable' | 'Artifact missing' | 'Unknown'

export interface User {
  id: string
  name: string
  email: string
  role: UserRole
  organization: string
  permissions: string[]
}

export interface PaginatedResponse<T> {
  items: T[]
  page: number
  limit: number
  total: number
  pages: number
}

export interface Vehicle {
  id: string
  number: string
  registrationNumber: string
  vehicleCode: string
  imageUrl: string | null
  category: string
  brand?: string
  modelName?: string
  year?: number
  batteryCapacityKwh?: number
  model: string
  type: string
  assignedDriver: string
  mileage: number
  status: 'Active' | 'Maintenance' | 'In Transit' | 'Offline' | 'Retired'
  backendStatus?: string
  risk: RiskLevel
  route?: string
  lastServiceDate?: string
  nextServiceDueDate?: string
}

export interface ReadinessRecommendation {
  type: string
  severity: string
  message: string
}

export interface VehicleReadiness {
  vehicleId: string
  registrationNumber: string
  vehicleCode: string
  category: string
  operationalStatus: string
  healthStatus: string
  predictionRisk: string | null
  eligible: boolean
  readinessStatus: 'ready' | 'warning' | 'blocked'
  blockingReasons: string[]
  warnings: string[]
}

export interface FleetReadiness {
  forecastDate: string | null
  requiredVehicles: number
  eligibleVehicles: number
  warningVehicles: number
  blockedVehicles: number
  maintenanceVehicles: number
  capacityGap: number
  highDemandZones: Array<Record<string, unknown>>
  vehicleReadiness: VehicleReadiness[]
  operationalConflicts: ReadinessRecommendation[]
  recommendations: ReadinessRecommendation[]
  dataContext: string
  dataContextNote: string
}

export interface AssignmentValidation {
  eligible: boolean
  readinessStatus: string
  vehicleRegistration: string
  vehicleCode: string
  vehicleType: string
  routeCode: string
  blockingReasons: string[]
  warnings: string[]
  maintenanceRisk: string
  routeDelayProbability: number
}

export interface VehiclePart {
  id: string
  vehicleId: string
  name: string
  lastService: string
  failures: number
  risk: RiskLevel
  riskScore: number
  status: string
  predictedNext: string
  note: string
  category?: string
  isActive?: boolean
  archivedAt?: string | null
}

export interface EvPartCatalogItem {
  key: string
  name: string
  category: string
  description: string
  mlSupported: boolean
  mlSignalGroup: string | null
}

export interface MaintenanceRecord {
  id: string
  vehicleId: string
  date: string
  vehicle: string
  partName: string
  maintenanceType: string
  priority: string
  service: string
  technician: string
  cost: string
  costValue: number
  status: 'Completed' | 'Cancelled' | 'Pending Parts' | 'Overdue'
}

export interface DeliveryOrder {
  id: string
  orderCode?: string
  customer: string
  priority: 'Critical' | 'High' | 'Standard'
  timeWindow: string
  zone: string
  location: string
  status: 'Unassigned' | 'Routed' | 'In Transit'
  backendStatus?: string
  pickupLatitude?: number
  pickupLongitude?: number
  dropLatitude?: number
  dropLongitude?: number
  pickupAddress?: string
  dropAddress?: string
  zoneId?: string
  scheduledDate?: string
  assignedVehicleId?: string | null
  assignedDriverId?: string | null
}

export interface RouteStop {
  sequence: number
  name: string
  eta: string
  loadDrop: string
  status: 'Origin' | 'Pending' | 'Complete'
  latitude: number | null
  longitude: number | null
}

export interface MapCoordinate {
  latitude: number
  longitude: number
}

export interface RoutePlan {
  id: string
  vehicle: string
  driver: string
  distance: string
  eta: string
  capacityUse: number
  stops: RouteStop[]
  mapPath: MapCoordinate[]
  warning: string
  weatherAvailable?: boolean
  weatherWarnings?: string[]
}

export interface TripEvent {
  id: string
  time: string
  title: string
  description: string
  severity: 'info' | 'warning' | 'critical'
}

export interface LiveTrip {
  routeId: string
  routeCode: string
  routeName: string
  driverName: string
  vehicleCode: string
  tripStatus: string
  routeStatus: string
  latestLocation: {
    latitude: number
    longitude: number
    recordedAt: string
  } | null
  progress: {
    totalStops: number
    completedStops: number
  }
  latestEvent: TripEvent | null
}

export interface LiveTripLocation {
  id: string
  latitude: number
  longitude: number
  recordedAt: string
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
  zoneId?: string
  zone: string
  currentVolume: number
  predictedVolume: number
  variance: number
  action: string
  rawMappedForecast?: number
  calibrationStatus?: 'insufficient_history' | 'active'
  calibrationFactor?: number | null
  historyDays?: number
}

export interface OperationalZoneOption {
  id: string
  name: string
  latitude: number
  longitude: number
  serviceRadiusKm: number
}
