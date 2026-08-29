import { describe, expect, it } from 'vitest'
import { routeSetWorkflow } from './routeSetWorkflow'
import type { LoadPlan } from '../loadOptimization/types'
import type { RouteSet } from '../../types'

const plan = (assigned: boolean): LoadPlan => ({
  plan_id: 'plan-1', job_id: 'job-1', revision: 1, delivery_date: '2026-08-29', delivery_period: 'first_half', status: 'approved',
  regions: [], exceptions: [], pareto_options: [], created_at: '2026-08-29T00:00:00Z',
  selected_option: { option_id: 'balanced', label: 'Balanced', strategy: 'balanced', objectives: { vehicle_count: 1, unused_volume_m3: 1, unassigned_parcels: 0 }, loads: [{ load_id: 'load-1', region_id: 1, vehicle_type_code: 'van', capacity_kg: 100, capacity_m3: 2, cargo_length_cm: 200, cargo_width_cm: 120, cargo_height_cm: 120, used_weight_kg: 20, used_volume_m3: 1, parcel_count: 1, parcel_ids: ['parcel-1'], placements: [], loading_sequence: [], requires_refrigeration: false, hazardous: false, assigned_vehicle_id: assigned ? 'vehicle-1' : null }] },
})

const routeSet = (status: RouteSet['status'], driver = 'Unassigned'): RouteSet => ({
  routeSetId: 'set-1', loadPlanId: 'plan-1', consolidationId: 'PCID1', optionId: 'balanced', deliveryDate: '2026-08-29', deliveryPeriod: 'first_half', expectedRouteCount: 1, status,
  routes: [{ id: 'route-1', vehicle: 'vehicle-1', driver, distance: '10 cost', eta: '20 min', capacityUse: 50, stops: [], mapPath: [], warning: '' }],
})

describe('routeSetWorkflow', () => {
  it('requires every physical vehicle before route generation', () => {
    expect(routeSetWorkflow(plan(false), null).canGenerateRoutes).toBe(false)
    expect(routeSetWorkflow(plan(true), null).canGenerateRoutes).toBe(true)
  })

  it('requires route approval before driver assignment and every driver before dispatch', () => {
    expect(routeSetWorkflow(plan(true), routeSet('review_required')).canApproveRoutes).toBe(true)
    expect(routeSetWorkflow(plan(true), routeSet('review_required')).canAssignDrivers).toBe(false)
    expect(routeSetWorkflow(plan(true), routeSet('approved', 'driver-1')).canDispatch).toBe(true)
  })
})
