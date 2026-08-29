export interface LoadPlacement {
  parcel_id: string
  x_cm: number
  y_cm: number
  z_cm: number
  length_cm: number
  width_cm: number
  height_cm: number
  fragile?: boolean
  fixed_orientation?: boolean
  layer?: number
}

export interface VirtualLoad {
  load_id: string
  region_id: number
  vehicle_type_code: string
  capacity_kg: number
  capacity_m3: number
  cargo_length_cm: number
  cargo_width_cm: number
  cargo_height_cm: number
  assigned_cargo_length_cm?: number | null
  assigned_cargo_width_cm?: number | null
  assigned_cargo_height_cm?: number | null
  used_weight_kg: number
  used_volume_m3: number
  parcel_count: number
  parcel_ids: string[]
  placements: LoadPlacement[]
  loading_sequence: string[]
  requires_refrigeration: boolean
  hazardous: boolean
  assigned_vehicle_id?: string | null
  estimated_route_km?: number
  route_preview?: Array<{ type: 'branch' | 'parcel'; parcel_id?: string; latitude: number; longitude: number }>
}

export interface ParetoOption {
  option_id: string
  label: string
  strategy: string
  objectives: { vehicle_count: number; unused_volume_m3: number; unassigned_parcels: number; estimated_route_km?: number }
  loads: VirtualLoad[]
  exceptions?: Array<{ parcel_id: string; reasons: string[] }>
}

export interface LoadPlan {
  plan_id: string
  job_id: string
  revision: number
  delivery_date: string
  delivery_period: 'first_half' | 'second_half'
  status: 'review_required' | 'approved' | 'failed' | 'cancelled' | 'superseded'
  regions: Array<{ region_id: number; parcel_count: number; centroid: { latitude: number; longitude: number }; parcel_ids: string[] }>
  exceptions: Array<{ parcel_id: string; reasons: string[] }>
  pareto_options: ParetoOption[]
  selected_option: ParetoOption | null
  created_at: string
  consolidation_id?: string | null
  route_set_id?: string | null
}

export interface LoadJob {
  job_id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
  stage: string
  progress_percent: number
  plan_id?: string | null
  error?: string | null
}

export type CandidateGenerationStatus = 'not_started' | 'queued' | 'running' | 'completed' | 'ready' | 'approved' | 'failed' | 'cancelled'

export interface ConsolidationPlanningState {
  consolidation: ParcelConsolidation
  job: LoadJob | null
  plan: LoadPlan | null
  status: CandidateGenerationStatus
  can_generate: boolean
  can_retry: boolean
}

export interface LoadEligibility {
  batch_key: string
  delivery_date: string
  delivery_period: 'first_half' | 'second_half'
  eligible_count: number
  exception_count: number
  excluded_count: number
  demand_context?: { available: boolean; required_vehicle_shifts: number | null; high_demand_zones: string[]; model_run_id?: string }
  eligible_orders: Array<{ id: string; order_code: string; parcel_weight: number; load_profile?: { volume_m3?: number } }>
  exceptions: Array<{ order_id: string; reasons: string[] }>
  excluded_orders: Array<{ order_id: string; reasons: string[] }>
}

export interface LoadRegion {
  region_id: number
  parcel_count: number
  total_weight_kg?: number
  total_volume_m3?: number
  centroid: { latitude: number; longitude: number }
  parcel_ids: string[]
}

export interface LoadConsolidation {
  batch_key: string
  delivery_date: string
  delivery_period: 'first_half' | 'second_half'
  parcel_count: number
  eligible_count: number
  exception_count: number
  excluded_count: number
  cluster_method: string
  parcel_points: LoadParcelPoint[]
  regions: LoadRegion[]
  exceptions: LoadEligibility['exceptions']
  excluded_orders: LoadEligibility['excluded_orders']
  demand_context?: LoadEligibility['demand_context']
}

export interface LoadParcelPoint {
  parcel_id: string
  order_code: string
  zone_id?: string | null
  drop_address?: string | null
  latitude: number
  longitude: number
  region_id: number
}

export interface ParcelConsolidation {
  consolidation_id: string
  status: 'active' | 'planning' | 'planned' | 'approved' | 'routed' | 'superseded' | 'cancelled'
  delivery_date: string
  delivery_period: 'first_half' | 'second_half'
  parcel_count: number
  parcel_ids: string[]
  parcel_points: LoadParcelPoint[]
  regions: LoadRegion[]
  cluster_method: string
  active_plan_id?: string | null
  active_job_id?: string | null
  created_at?: string
}

export interface LoadVehicleType {
  code: string
  label: string
  category: 'car' | 'van' | 'truck' | 'bus'
  capacity_kg: number
  capacity_m3: number
  max_parcels: number
  max_stack_layers: number
  max_stack_weight_kg: number
  cargo_length_cm: number
  cargo_width_cm: number
  cargo_height_cm: number
  is_refrigerated: boolean
  is_hazmat_certified: boolean
  temp_min_celsius?: number
  temp_max_celsius?: number
  registered_vehicle_count: number
  active_vehicle_count: number
}

export interface LoadOptimizationScope {
  deliveryDate: string
  deliveryPeriod: 'first_half' | 'second_half'
  orderIds: string[]
  scopeLabel: string
}

export interface VehicleSuggestion {
  load_id: string
  matches: Array<{ vehicle: { id: string; registration_number: string; vehicle_category?: string }; compatibility: { eligible: boolean; reasons: string[] } }>
}
