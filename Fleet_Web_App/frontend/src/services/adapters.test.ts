import { describe, expect, it } from 'vitest'
import { mapDeliveryOrder, mapDemandForecast, mapDemandZone, mapInspection, mapInspectionAssignee, mapMaintenancePrediction, mapMaintenanceRecord, mapPredictionReview, mapRoutePlan, mapVehicle } from './adapters'

describe('Phase 11 API adapters', () => {
  it('numbers route delivery stops independently from branch endpoints', () => {
    const route = mapRoutePlan({
      id: 'route-1',
      optimized_stop_order: [
        { type: 'depot', latitude: 6.9271, longitude: 79.8612 },
        { type: 'delivery', order_id: 'one', order_code: 'ORD-001', latitude: 6.91, longitude: 79.88 },
        { type: 'delivery', order_id: 'two', order_code: 'ORD-002', latitude: 6.92, longitude: 79.89 },
        { type: 'depot', latitude: 6.9271, longitude: 79.8612 },
      ],
    })

    expect(route.stops.filter((stop) => stop.status === 'Pending').map((stop) => stop.sequence)).toEqual([1, 2])
  })

  it('uses registration number as the primary vehicle identifier', () => {
    const vehicle = mapVehicle({
      id: 'vehicle-1',
      registration_number: 'WP CAA-1234',
      vehicle_code: 'EV-FLEET-001',
      vehicle_type: 'electric_van',
      brand: 'BYD',
      model: 'T3',
      status: 'active',
      health_status: 'healthy',
    })

    expect(vehicle.number).toBe('WP CAA-1234')
    expect(vehicle.registrationNumber).toBe('WP CAA-1234')
    expect(vehicle.vehicleCode).toBe('EV-FLEET-001')
    expect(vehicle.category).toBe('Electric Van')
  })

  it('maps a managed vehicle image to the backend media origin', () => {
    const vehicle = mapVehicle({
      id: 'vehicle-1',
      registration_number: 'WP CAA-1234',
      vehicle_code: 'EV-FLEET-001',
      vehicle_type: 'electric_van',
      image_url: '/media/vehicles/vehicle.webp',
    })

    expect(vehicle.imageUrl).toBe(`${window.location.origin}/media/vehicles/vehicle.webp`)
  })

  it('maps canonical fleet fields independently from legacy vehicle type', () => {
    const vehicle = mapVehicle({
      id: 'vehicle-2', registration_number: 'WP CAB-4421', vehicle_code: 'FLEET-4421',
      vehicle_type: 'diesel_truck', vehicle_category: 'truck', fuel_type: 'diesel',
      in_service_date: '2022-04-08T00:00:00Z', payload_capacity_kg: 4200,
      load_profile: { profile_code: 'HEAVY_TRUCK', capacity_m3: 24, cargo_length_cm: 620, cargo_width_cm: 240, cargo_height_cm: 240 },
    })

    expect(vehicle.category).toBe('Truck')
    expect(vehicle.vehicleCategory).toBe('truck')
    expect(vehicle.fuelType).toBe('diesel')
    expect(vehicle.inServiceDate).toBe('2022-04-08')
    expect(vehicle.payloadCapacityKg).toBe(4200)
    expect(vehicle.loadProfile?.profileCode).toBe('HEAVY_TRUCK')
    expect(vehicle.loadProfile?.capacityM3).toBe(24)
  })

  it('uses the latest assessment risk for the vehicle registry', () => {
    const vehicle = mapVehicle({
      id: 'vehicle-3', registration_number: 'WP CAC-5512', vehicle_code: 'FLEET-5512',
      vehicle_type: 'diesel_truck', health_status: 'healthy', latest_assessment_risk: 'critical',
    })

    expect(vehicle.risk).toBe('critical')
  })

  it('uses enriched Sri Lankan zone labels for operational views', () => {
    const raw = {
      zone_id: 'SP_sao_paulo',
      source_zone_id: 'SP_sao_paulo',
      operational_zone_id: 'LK_colombo_central',
      zone_display_name: 'Colombo Central',
      predicted_demand: 62,
    }

    expect(mapDemandForecast(raw).zone).toBe('Colombo Central')
    expect(mapDemandZone(raw).id).toBe('LK_colombo_central')
    expect(mapDemandZone(raw).name).toBe('Colombo Central')
    expect(mapDeliveryOrder(raw).zone).toBe('Colombo Central')
  })

  it('maps the active Colombo demand contract without calibration aliases', () => {
    const forecast = mapDemandForecast({
      operational_zone_id: 'LK_borella', zone_display_name: 'Borella', date: '2027-01-02T00:00:00Z',
      predicted_demand: 21.4, local_actual_demand: 19, variance_orders: 2.4, variance_percentage: 12.6,
      baseline_forecast: 20.2, lower_bound: 15.1, upper_bound: 27.8, demand_level: 'high',
      estimated_required_vehicles: 2, recommended_action: 'Reserve additional capacity',
      model_version: 'fleetopt-demand-synthetic-v1', generated_at: '2026-08-27T10:00:00Z',
    })

    expect(forecast).toMatchObject({
      zoneId: 'LK_borella', zone: 'Borella', date: '2027-01-02', currentVolume: 19,
      actualAvailable: true, predictedVolume: 21, variance: 12.6, varianceOrders: 2.4,
      baselineForecast: 20.2, lowerBound: 15.1, upperBound: 27.8, demandLevel: 'high',
      requiredVehicles: 2, modelVersion: 'fleetopt-demand-synthetic-v1',
    })
  })

  it('maps parcel delivery date, period, and fixed branch origin', () => {
    const parcel = mapDeliveryOrder({
      id: 'order-1', order_code: 'ORD-1', customer_name: 'Customer', priority: 'medium', delivery_status: 'pending',
      delivery_date: '2026-08-30', delivery_period: 'first_half',
      pickup_address: 'Colombo Central Branch, Colombo, Sri Lanka', pickup_source: 'colombo_branch',
      pickup_latitude: 6.9271, pickup_longitude: 79.8612, drop_latitude: 6.8649, drop_longitude: 79.8997,
      load_profile: { length_cm: 50, width_cm: 40, height_cm: 30, volume_m3: 0.06, fragile: true, optimization_eligible: true, data_quality_flags: [] },
      load_planning_status: 'unplanned',
    })

    expect(parcel.deliveryDate).toBe('2026-08-30')
    expect(parcel.deliveryPeriod).toBe('first_half')
    expect(parcel.pickupSource).toBe('colombo_branch')
    expect(parcel.loadProfile?.lengthCm).toBe(50)
    expect(parcel.loadProfile?.optimizationEligible).toBe(true)
    expect(parcel.loadPlanningStatus).toBe('unplanned')
  })

  it('preserves an unavailable actual as unavailable instead of zero evidence', () => {
    const forecast = mapDemandForecast({
      operational_zone_id: 'LK_wattala', date: '2027-01-03', predicted_demand: 11,
      local_actual_demand: null, variance_orders: null, variance_percentage: null,
      demand_level: 'low', estimated_required_vehicles: 1,
    })

    expect(forecast.currentVolume).toBe(0)
    expect(forecast.actualAvailable).toBe(false)
    expect(forecast.varianceOrders).toBeNull()
  })
})

describe('maintenance intelligence adapters', () => {
  it('maps the sensor-free prediction contract and guarded planning window', () => {
    const prediction = mapMaintenancePrediction({
      id: 'prediction-1', vehicle_id: 'vehicle-1', vehicle_registration: 'WP CAA-1234', risk_level: 'high',
      failure_probability_30_days: 0.18, failure_probability_2000_km: 0.09,
      system_risks: [{ system: 'braking', probability: 0.71, risk_level: 'high' }, { system: 'tires', probability: 0.44, risk_level: 'medium' }],
      planning_status: 'planning_window_available',
      planning_window: { minimum_days: 14, maximum_days: 40, minimum_km: 600, maximum_km: 1800 },
      data_quality: 'good', defaulted_fields: ['route_roughness_mean_30d'], review_status: 'pending',
      dispatch_hold: true, feature_snapshot_version: '3.0', model_version: 'fleetopt-sensor-free-pm-v1', created_at: '2026-08-24T06:30:00Z',
      prediction_review_id: 'review-22',
    })

    expect(prediction.probability30Days).toBe(0.18)
    expect(prediction.probability2000Km).toBe(0.09)
    expect(prediction.systemRisks[0]).toMatchObject({ name: 'Braking', probability: 0.71 })
    expect(prediction.planningWindow).toMatchObject({ minimumDays: 14, maximumKm: 1800 })
    expect(prediction.reviewStatus).toBe('pending')
    expect(prediction.dispatchHold).toBe(true)
    expect(prediction.reviewId).toBe('review-22')
  })

  it('keeps legacy prediction aliases usable during rollout', () => {
    const prediction = mapMaintenancePrediction({
      prediction_id: 'legacy-1', vehicle_id: 'vehicle-2', failure_probability: 0.31,
      maintenance_type_name: 'Brake inspection', risk_level: 'critical', predicted_rul: 21, rul_unit: 'days',
    })

    expect(prediction.probability30Days).toBe(0.31)
    expect(prediction.systemRisks[0].name).toBe('Brake Inspection')
    expect(prediction.planningWindow?.maximumDays).toBe(21)
  })

  it('maps nested guarded day and kilometre planning bounds', () => {
    const prediction = mapMaintenancePrediction({
      id: 'prediction-nested', vehicle_id: 'vehicle-3', risk_level: 'high',
      planning_status: 'planning_window_available',
      planning_window: { days: { lower: 9, upper: 28 }, km: { lower: 450, upper: 1600 } },
    })

    expect(prediction.planningWindow).toEqual({ minimumDays: 9, maximumDays: 28, minimumKm: 450, maximumKm: 1600 })
  })

  it('maps review audit and canonical maintenance classifications', () => {
    const review = mapPredictionReview({ id: 'review-1', vehicle_id: 'vehicle-1', prediction_id: 'prediction-1', status: 'pending', created_at: '2026-08-24T06:30:00Z', vehicle_registration: 'WP CAA-1234', feature_hash: 'hash-1' })
    const record = mapMaintenanceRecord({ id: 'record-1', vehicle_id: 'vehicle-1', part_name: 'Brake Pads', maintenance_type: 'corrective', maintenance_system: 'braking', event_kind: 'corrective_repair', service_date: '2026-08-24', status: 'scheduled' })

    expect(review).toMatchObject({ id: 'review-1', vehicleRegistration: 'WP CAA-1234', status: 'pending' })
    expect(record.maintenanceSystem).toBe('braking')
    expect(record.eventKind).toBe('corrective_repair')
  })

  it('maps linked work-order lifecycle and audit fields without dropping legacy fields', () => {
    const record = mapMaintenanceRecord({ id: 'work-7', vehicle_id: 'vehicle-1', service_date: '2026-08-29T09:00:00Z', part_name: 'Brake Pads', maintenance_type: 'corrective', maintenance_system: 'braking', issue_type: 'Brake wear', work_order_status: 'in_progress', inspection_id: 'inspection-2', assessment_id: 'assessment-3', estimated_cost: 18000, actual_cost: 17500, started_at: '2026-08-29T10:00:00Z', completed_at: null, completion_evidence: null, cancellation_reason: null, created_at: '2026-08-28T08:00:00Z', updated_at: '2026-08-29T10:00:00Z', status: 'in_progress' })
    expect(record).toMatchObject({ id: 'work-7', serviceDate: '2026-08-29T09:00:00Z', issueType: 'Brake wear', workOrderStatus: 'in_progress', inspectionId: 'inspection-2', assessmentId: 'assessment-3', estimatedCost: 18000, actualCost: 17500, startedAt: '2026-08-29T10:00:00Z', createdAt: '2026-08-28T08:00:00Z' })
    expect(record.service).toContain('Brake Pads')
  })

  it('maps inspection lifecycle data and safe assignee fields', () => {
    const inspection = mapInspection({
      id: 'inspection-1', vehicle_id: 'vehicle-1', assessment_id: 'assessment-1', feature_hash: 'hash-123',
      status: 'assigned', is_active: true, priority: 'high', inspection_areas: ['Braking'], assigned_to: 'user-1',
      draft_checklist: [{ key: 'tires', label: 'Tires', outcome: 'failed', remark: 'Low tread depth' }],
      draft_summary: 'Inspection underway', draft_saved_by: 'user-1', draft_saved_at: '2026-08-27T08:30:00Z',
      checklist: [{ key: 'brakes', label: 'Brake operation', outcome: 'passed', remark: null }],
      created_by: 'admin-1', created_at: '2026-08-27T08:00:00Z', updated_at: '2026-08-27T08:30:00Z',
    })
    const assignee = mapInspectionAssignee({ id: 'user-1', full_name: 'M. Perera', role: 'maintenance_manager', email: 'hidden@example.com' })

    expect(inspection).toMatchObject({ id: 'inspection-1', vehicleId: 'vehicle-1', status: 'assigned', priority: 'high', inspectionAreas: ['Braking'], assignedTo: 'user-1' })
    expect(inspection.checklist[0]).toEqual({ key: 'brakes', label: 'Brake operation', outcome: 'passed', remark: null })
    expect(inspection.draftChecklist[0]).toEqual({ key: 'tires', label: 'Tires', outcome: 'failed', remark: 'Low tread depth' })
    expect(inspection).toMatchObject({ draftSummary: 'Inspection underway', draftSavedBy: 'user-1', draftSavedAt: '2026-08-27T08:30:00Z' })
    expect(assignee).toEqual({ id: 'user-1', fullName: 'M. Perera', role: 'maintenance_manager' })
    expect(assignee).not.toHaveProperty('email')
  })
})
