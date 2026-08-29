interface OptimizationSelection {
  deliveryOrderIds: string[]
  driverId: string
  vehicleId: string
  loadContext?: { planId: string; loadId: string } | null
}

export function buildOptimizationPayload({ deliveryOrderIds, driverId, vehicleId, loadContext }: OptimizationSelection) {
  if (!deliveryOrderIds.length) throw new Error('Select at least one pending delivery before optimization.')
  if (!vehicleId) throw new Error('Select an eligible vehicle before optimization.')
  if (!driverId) throw new Error('Select an enrolled driver before optimization.')

  return {
    delivery_order_ids: [...new Set(deliveryOrderIds)],
    vehicle_id: vehicleId,
    driver_id: driverId,
    ...(loadContext ? { load_plan_id: loadContext.planId, load_id: loadContext.loadId } : {}),
    use_ml_cost: true,
    include_demand_context: true,
    include_maintenance_context: true,
    include_weather_context: true,
    save_route: true,
  }
}
