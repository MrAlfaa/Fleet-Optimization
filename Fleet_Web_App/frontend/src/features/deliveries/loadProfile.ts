import type { ParcelLoadProfileInput } from '../../services/operationsService'

function requiredPositiveNumber(form: FormData, name: string, label: string) {
  const value = Number(String(form.get(name) ?? '').trim())
  if (!Number.isFinite(value) || value <= 0) throw new Error(`${label} must be greater than zero.`)
  return value
}
function optionalNumber(form: FormData, name: string) {
  const raw = String(form.get(name) ?? '').trim()
  if (!raw) return undefined
  const value = Number(raw)
  if (!Number.isFinite(value)) throw new Error(`${name.replaceAll('_', ' ')} must be a number.`)
  return value
}

export function parcelLoadProfileFromForm(form: FormData): ParcelLoadProfileInput {
  const refrigerated = form.has('requires_refrigeration')
  const hazardous = form.has('hazardous')
  const tempMin = optionalNumber(form, 'temp_min_celsius')
  const tempMax = optionalNumber(form, 'temp_max_celsius')
  const hazmatClass = String(form.get('hazmat_class') ?? '').trim()
  if (refrigerated && (tempMin === undefined || tempMax === undefined || tempMin >= tempMax)) {
    throw new Error('A valid temperature range is required for refrigerated parcels.')
  }
  if (hazardous && !hazmatClass) throw new Error('Hazmat class is required for hazardous parcels.')
  return {
    length_cm: requiredPositiveNumber(form, 'length_cm', 'Parcel length'),
    width_cm: requiredPositiveNumber(form, 'width_cm', 'Parcel width'),
    height_cm: requiredPositiveNumber(form, 'height_cm', 'Parcel height'),
    fragile: form.has('fragile'),
    stackable: form.has('stackable'),
    max_stack_weight_kg: optionalNumber(form, 'max_stack_weight_kg') ?? 0,
    loading_orientation_fixed: form.has('loading_orientation_fixed'),
    hazardous,
    hazmat_class: hazardous ? hazmatClass : undefined,
    requires_refrigeration: refrigerated,
    temp_min_celsius: refrigerated ? tempMin : undefined,
    temp_max_celsius: refrigerated ? tempMax : undefined,
    two_person_lift: form.has('two_person_lift'),
    do_not_tilt: form.has('do_not_tilt'),
    service_type: String(form.get('service_type') || 'door_to_door') as ParcelLoadProfileInput['service_type'],
  }
}
