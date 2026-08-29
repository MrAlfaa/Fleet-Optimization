import { describe, expect, it } from 'vitest'
import type { LoadParcelPoint, ParetoOption } from './types'
import { buildCandidateRoutePreview } from './candidateRoutePreview'

describe('candidate route preview', () => {
  it('renders only deliverable parcels as consecutively numbered drop points', () => {
    const parcelPoints: LoadParcelPoint[] = Array.from({ length: 15 }, (_, index) => ({
      parcel_id: `parcel-${index + 1}`,
      order_code: `ORD-${String(index + 1).padStart(3, '0')}`,
      drop_address: `Address ${index + 1}`,
      latitude: 6.8 + index * 0.001,
      longitude: 79.8 + index * 0.001,
      region_id: index < 6 ? 0 : 1,
    }))
    const option: ParetoOption = {
      option_id: 'maximum-buffer',
      label: 'Maximum Buffer',
      strategy: 'buffer',
      objectives: { vehicle_count: 2, unused_volume_m3: 2, unassigned_parcels: 4 },
      exceptions: [12, 13, 14, 15].map((id) => ({ parcel_id: `parcel-${id}`, reasons: ['capacity'] })),
      loads: [
        {
          load_id: 'load-a', region_id: 0, vehicle_type_code: 'van', capacity_kg: 1000, capacity_m3: 8,
          cargo_length_cm: 300, cargo_width_cm: 180, cargo_height_cm: 180,
          used_weight_kg: 120, used_volume_m3: 1, parcel_count: 6,
          parcel_ids: ['parcel-3', 'parcel-1', 'parcel-2', 'parcel-4', 'parcel-5', 'parcel-6'],
          placements: [], loading_sequence: [], requires_refrigeration: false, hazardous: false,
          route_preview: [
            { type: 'branch', latitude: 6.9271, longitude: 79.8612 },
            ...['parcel-3', 'parcel-1', 'parcel-2', 'parcel-4', 'parcel-5', 'parcel-6'].map((parcel_id) => ({
              type: 'parcel' as const,
              parcel_id,
              latitude: parcelPoints.find((point) => point.parcel_id === parcel_id)!.latitude,
              longitude: parcelPoints.find((point) => point.parcel_id === parcel_id)!.longitude,
            })),
            { type: 'branch', latitude: 6.9271, longitude: 79.8612 },
          ],
        },
        {
          load_id: 'load-b', region_id: 1, vehicle_type_code: 'van', capacity_kg: 1000, capacity_m3: 8,
          cargo_length_cm: 300, cargo_width_cm: 180, cargo_height_cm: 180,
          used_weight_kg: 100, used_volume_m3: 1, parcel_count: 5,
          parcel_ids: ['parcel-7', 'parcel-8', 'parcel-9', 'parcel-10', 'parcel-11'],
          placements: [], loading_sequence: [], requires_refrigeration: false, hazardous: false,
          route_preview: [
            { type: 'branch', latitude: 6.9271, longitude: 79.8612 },
            ...['parcel-7', 'parcel-8', 'parcel-9', 'parcel-10', 'parcel-11'].map((parcel_id) => ({
              type: 'parcel' as const,
              parcel_id,
              latitude: parcelPoints.find((point) => point.parcel_id === parcel_id)!.latitude,
              longitude: parcelPoints.find((point) => point.parcel_id === parcel_id)!.longitude,
            })),
            { type: 'branch', latitude: 6.9271, longitude: 79.8612 },
          ],
        },
      ],
    }

    const preview = buildCandidateRoutePreview(option, parcelPoints)

    expect(preview.dropMarkers).toHaveLength(11)
    expect(preview.dropMarkers.map((marker) => marker.label)).toEqual(Array.from({ length: 11 }, (_, index) => String(index + 1)))
    expect(preview.dropMarkers.map((marker) => marker.id)).not.toContain('parcel-12')
    expect(preview.dropMarkers[0].title).toContain('ORD-003')
    expect(preview.polylines).toHaveLength(2)
  })

  it('renders every parcel when the candidate has no exceptions', () => {
    const parcelPoints: LoadParcelPoint[] = Array.from({ length: 15 }, (_, index) => ({
      parcel_id: `parcel-${index + 1}`,
      order_code: `ORD-${index + 1}`,
      latitude: 6.8 + index * 0.001,
      longitude: 79.8 + index * 0.001,
      region_id: 0,
    }))
    const option: ParetoOption = {
      option_id: 'complete', label: 'Complete', strategy: 'balanced',
      objectives: { vehicle_count: 1, unused_volume_m3: 1, unassigned_parcels: 0 },
      exceptions: [],
      loads: [{
        load_id: 'load-all', region_id: 0, vehicle_type_code: 'truck', capacity_kg: 2500, capacity_m3: 14,
        cargo_length_cm: 450, cargo_width_cm: 210, cargo_height_cm: 210,
        used_weight_kg: 500, used_volume_m3: 5, parcel_count: 15,
        parcel_ids: parcelPoints.map((point) => point.parcel_id), placements: [], loading_sequence: [],
        requires_refrigeration: false, hazardous: false,
      }],
    }

    const preview = buildCandidateRoutePreview(option, parcelPoints)

    expect(preview.dropMarkers).toHaveLength(15)
    expect(preview.dropMarkers.at(-1)?.label).toBe('15')
  })
})
