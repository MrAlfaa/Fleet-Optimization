import { describe, expect, it } from 'vitest'
import { parcelLoadProfileFromForm } from './loadProfile'

function form(values: Record<string, string | boolean>) {
  const data = new FormData()
  Object.entries(values).forEach(([key, value]) => {
    if (typeof value === 'boolean') {
      if (value) data.set(key, 'on')
    } else data.set(key, value)
  })
  return data
}

describe('parcelLoadProfileFromForm', () => {
  it('creates the optimizer handling profile from parcel dimensions', () => {
    const profile = parcelLoadProfileFromForm(form({
      length_cm: '50', width_cm: '40', height_cm: '30', fragile: true,
      stackable: false, do_not_tilt: true, service_type: 'door_to_door',
    }))

    expect(profile).toMatchObject({
      length_cm: 50, width_cm: 40, height_cm: 30,
      fragile: true, stackable: false, do_not_tilt: true,
      service_type: 'door_to_door',
    })
  })

  it('rejects incomplete refrigerated handling requirements', () => {
    expect(() => parcelLoadProfileFromForm(form({
      length_cm: '50', width_cm: '40', height_cm: '30',
      requires_refrigeration: true, temp_min_celsius: '2', temp_max_celsius: '',
    }))).toThrow(/temperature range/i)
  })
})
