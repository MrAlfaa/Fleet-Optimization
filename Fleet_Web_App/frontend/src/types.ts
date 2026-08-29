export type UserRole = 'admin' | 'fleet_manager' | 'maintenance_manager' | 'route_planner' | 'driver'

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'
export type DemandLevel = 'low' | 'medium' | 'high' | 'very_high'

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
  vehicleCategory?: 'car' | 'van' | 'truck' | 'bus'
  fuelType?: 'electric' | 'hybrid' | 'diesel' | 'petrol'
  inServiceDate?: string
  payloadCapacityKg?: number
  loadProfile?: VehicleLoadProfile | null
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
  onboardingType?: 'brand_new' | 'existing_fleet'
  commissioningStatus?: 'not_started' | 'pending' | 'passed' | 'failed'
}

export interface VehicleLoadProfile {
  profileCode: string
  capacityM3: number
  cargoLengthCm: number
  cargoWidthCm: number
  cargoHeightCm: number
  maxParcels: number
  maxStackLayers: number
  vehicleMaxStackWeightKg: number
  isRefrigerated: boolean
  tempMinCelsius: number | null
  tempMaxCelsius: number | null
  isHazmatCertified: boolean
  hasTailLift: boolean
  availableFrom: string
  availableUntil: string
}

export type AssessmentEligibilityStatus =
  | 'profile_incomplete'
  | 'commissioning_required'
  | 'building_history'
  | 'ready_for_assessment'
  | 'assessment_current'
  | 'new_assessment_available'

export interface AssessmentEligibility {
  vehicleId: string
  onboardingType: 'brand_new' | 'existing_fleet'
  eligible: boolean
  status: AssessmentEligibilityStatus
  hasNewData: boolean
  missingProfileFields: string[]
  blockingReasons: string[]
  requirements: {
    profile: { complete: boolean }
    commissioningInspection: { complete: boolean }
    completedTrips: { current: number; required: number; complete: boolean }
    recordedDistanceKm: { current: number; required: number; complete: boolean }
    importedHistory: { current: number; complete: boolean }
    historyEvidence: { complete: boolean }
  }
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
  activeForecastRun: DemandForecastRun | null
  requiredVehicles: number
  eligibleVehicles: number
  warningVehicles: number
  blockedVehicles: number
  maintenanceVehicles: number
  capacityGap: number
  highDemandZones: ReadinessDemandZone[]
  vehicleReadiness: VehicleReadiness[]
  operationalConflicts: ReadinessRecommendation[]
  recommendations: ReadinessRecommendation[]
  dataContext: string
  dataContextNote: string
}

export interface ReadinessDemandZone {
  operationalZoneId: string
  zoneDisplayName: string
  predictedDemand: number
  actualDemand: number | null
  demandLevel: DemandLevel
  estimatedRequiredVehicles: number
  recommendedAction: string
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
  maintenanceSystem?: string
  eventKind?: 'scheduled_service' | 'corrective_repair' | 'breakdown' | 'inspection'
  priority: string
  service: string
  technician: string
  cost: string
  costValue: number
  status: 'Completed' | 'Cancelled' | 'Pending Parts' | 'Overdue'
  serviceDate?: string
  issueType?: string
  workOrderStatus?: MaintenanceWorkOrderStatus | null
  inspectionId?: string | null
  assessmentId?: string | null
  estimatedCost?: number | null
  actualCost?: number | null
  startedAt?: string | null
  completedAt?: string | null
  completionEvidence?: string | null
  cancellationReason?: string | null
  createdAt?: string
  updatedAt?: string
  notes?: string
  serviceCenter?: string
}

export type InspectionStatus =
  | 'pending'
  | 'assigned'
  | 'in_progress'
  | 'completed'
  | 'decision_pending'
  | 'maintenance_required'
  | 'returned_to_service'
  | 'cancelled'

export type InspectionPriority = 'low' | 'medium' | 'high' | 'critical'
export type InspectionDecision = 'maintenance_required' | 'returned_to_service'
export type InspectionCheckOutcome = 'passed' | 'failed' | 'not_applicable'
export type MaintenanceWorkOrderStatus = 'planned' | 'approved' | 'in_progress' | 'completed' | 'cancelled'

export interface InspectionChecklistItem {
  key: string
  label: string
  outcome: InspectionCheckOutcome
  remark: string | null
}

export interface VehicleMaintenanceInspection {
  id: string
  vehicleId: string
  inspectionType?: 'risk_assessment' | 'commissioning'
  assessmentId: string | null
  featureHash: string
  status: InspectionStatus
  isActive: boolean
  priority: InspectionPriority
  inspectionAreas: string[]
  notes: string | null
  checklist: InspectionChecklistItem[]
  summary: string | null
  draftChecklist: InspectionChecklistItem[]
  draftSummary: string | null
  draftSavedBy: string | null
  draftSavedAt: string | null
  assignedTo: string | null
  assignedBy: string | null
  assignedAt: string | null
  startedBy: string | null
  startedAt: string | null
  completedBy: string | null
  completedAt: string | null
  decision: InspectionDecision | null
  decisionNotes: string | null
  decidedBy: string | null
  decidedAt: string | null
  workOrderId: string | null
  cancellationReason: string | null
  createdBy: string
  createdAt: string
  updatedAt: string
}

export type MaintenanceSystem =
  | 'battery_system'
  | 'braking'
  | 'charging_system'
  | 'cooling_system'
  | 'electrical'
  | 'engine'
  | 'exhaust_dpf'
  | 'fuel_system'
  | 'ignition'
  | 'motor_drivetrain'
  | 'steering'
  | 'suspension'
  | 'thermal_system'
  | 'tires'

export interface InspectionAssignee {
  id: string
  fullName: string
  role: 'admin' | 'maintenance_manager'
}

export interface MaintenanceWorkOrder {
  id: string
  vehicleId: string
  inspectionId: string
  assessmentId: string
  status: MaintenanceWorkOrderStatus
  maintenanceSystem: string
  issueType: string
  priority: InspectionPriority
  estimatedCost: number | null
  actualCost: number | null
  startedAt: string | null
  completedAt: string | null
  completionEvidence: Record<string, unknown> | null
  cancellationReason: string | null
  createdAt: string
  updatedAt: string
}

export type MaintenanceReviewStatus = 'not_required' | 'pending' | 'cleared' | 'confirmed'

export interface MaintenanceSystemRisk {
  name: string
  key: string
  probability: number
  risk: RiskLevel
}

export interface MaintenancePlanningWindow {
  minimumDays?: number
  maximumDays?: number
  minimumKm?: number
  maximumKm?: number
}

export interface MaintenancePrediction {
  id: string
  vehicleId: string
  vehicleRegistration: string
  vehicleCode: string
  risk: RiskLevel
  probability30Days: number
  probability2000Km: number
  systemRisks: MaintenanceSystemRisk[]
  planningStatus: string
  planningWindow: MaintenancePlanningWindow | null
  dataQuality: string
  defaultedFields: string[]
  reviewStatus: MaintenanceReviewStatus
  dispatchHold: boolean
  modelVersion: string
  featureSchemaVersion: string
  createdAt: string
  featureHash: string
  reviewId: string
}

export interface MaintenanceReview {
  id: string
  vehicleId: string
  vehicleRegistration: string
  vehicleCode: string
  predictionId: string
  featureHash: string
  risk: RiskLevel
  status: Exclude<MaintenanceReviewStatus, 'not_required'>
  notes: string
  createdAt: string
  updatedAt: string
  resolvedAt: string | null
  resolvedBy: string
}

export interface PredictiveModelStatus {
  available: boolean
  loaded: boolean
  degraded: boolean
  modelVersion: string
  featureSchemaVersion: string
  message: string
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
  deliveryDate?: string
  deliveryPeriod?: 'first_half' | 'second_half'
  pickupSource?: string
  customerPhone?: string
  parcelWeight?: number | null
  parcelVolume?: number | null
  loadProfile?: ParcelLoadProfile | null
  loadPlanningStatus?: string
  activeConsolidationId?: string | null
  activeLoadPlanId?: string | null
  assignedVehicleId?: string | null
  assignedDriverId?: string | null
}

export interface ParcelLoadProfile {
  lengthCm: number
  widthCm: number
  heightCm: number
  volumeM3: number
  fragile: boolean
  stackable: boolean
  maxStackWeightKg: number
  loadingOrientationFixed: boolean
  hazardous: boolean
  hazmatClass: string | null
  requiresRefrigeration: boolean
  tempMinCelsius: number | null
  tempMaxCelsius: number | null
  twoPersonLift: boolean
  doNotTilt: boolean
  serviceType: string
  optimizationEligible: boolean
  eligibilityReasons: string[]
  dataQualityFlags: string[]
}

export interface RouteStop {
  sequence: number
  name: string
  eta: string
  loadDrop: string
  status: 'Origin' | 'Return' | 'Pending' | 'Complete'
  latitude: number | null
  longitude: number | null
}

export interface MapCoordinate {
  latitude: number
  longitude: number
}

export interface RoutePlan {
  id: string
  routeCode?: string
  status?: 'draft' | 'optimized' | 'approved' | 'dispatched' | 'in_progress' | 'completed' | 'cancelled'
  routeSetId?: string
  loadPlanId?: string
  loadId?: string
  consolidationId?: string
  vehicle: string
  driver: string
  distance: string
  eta: string
  capacityUse: number
  stops: RouteStop[]
  deliveryDate?: string
  deliveryPeriod?: 'first_half' | 'second_half'
  mapPath: MapCoordinate[]
  geometrySource?: 'osrm' | 'fallback'
  geometryCached?: boolean
  warning: string
  weatherAvailable?: boolean
  weatherWarnings?: string[]
  averageDelayProbability?: number
}

export interface RouteSet {
  routeSetId: string
  loadPlanId: string
  consolidationId: string
  optionId: string
  deliveryDate: string
  deliveryPeriod: 'first_half' | 'second_half'
  expectedRouteCount: number
  status: 'generating' | 'review_required' | 'approved' | 'dispatching' | 'dispatched' | 'failed' | 'cancelled'
  routes: RoutePlan[]
  error?: string | null
}

export interface OperationalBranch {
  id: string
  name: string
  address: string
  latitude: number
  longitude: number
  timezone: string
  deliveryPeriods: Array<{
    id: 'first_half' | 'second_half'
    label: string
    start: string
    end: string
  }>
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
  actualAvailable?: boolean
  demandLevel?: DemandLevel
  requiredVehicles?: number
  varianceOrders?: number | null
}

export interface DemandForecast {
  zoneId?: string
  zone: string
  date?: string
  currentVolume: number
  actualAvailable?: boolean
  predictedVolume: number
  variance: number
  varianceOrders?: number | null
  action: string
  demandLevel?: DemandLevel
  requiredVehicles?: number
  baselineForecast?: number | null
  lowerBound?: number | null
  upperBound?: number | null
  modelVersion?: string
  generatedAt?: string
}

export type DemandForecastHorizon = 7 | 14 | 30

export interface DemandForecastPlanningWindow {
  basis: string
  dataset_end_date: string | null
  forecast_start_date: string | null
  forecast_end_date: string | null
  horizon_days: number
}

export interface DemandForecastRun {
  model_run_id: string
  model_version: string | null
  forecast_start_date: string | null
  forecast_end_date: string | null
  horizon_days: number
  records_generated: number
  zones_count: number
  source_requested: string | null
  effective_source?: string | null
  fallback_used?: boolean
  run_type: string | null
  generated_at?: string | null
  activated_at: string | null
  request_fingerprint: string | null
  status?: string | null
  planning_window: DemandForecastPlanningWindow
}

export interface DemandForecastRunDetail {
  run: DemandForecastRun
  items: DemandForecast[]
  total: number
}

export interface DemandModelStatus {
  operational_state?: string
  loaded?: boolean
  available?: boolean
  active_run: DemandForecastRun | null
}

export interface DemandForecastRefreshResponse {
  reused_active_run: boolean
  active_run: DemandForecastRun
}

export interface OperationalZoneOption {
  id: string
  name: string
  latitude: number
  longitude: number
  serviceRadiusKm: number
}
