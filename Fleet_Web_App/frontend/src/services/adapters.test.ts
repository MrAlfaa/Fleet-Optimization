import { describe, expect, it } from 'vitest'
import { mapDeliveryOrder, mapDemandForecast, mapDemandZone, mapVehicle } from './adapters'

describe('Phase 11 API adapters', () => {
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
})
