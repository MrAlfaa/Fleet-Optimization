import { ImagePlus, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { fleetService } from '../services/fleetService'
import type { Vehicle } from '../types'
import { PrimaryButton, SecondaryButton } from './UI'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from './ModalLayout'


const MAX_IMAGE_BYTES = 5 * 1024 * 1024
const ACCEPTED_IMAGE_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])


export function VehicleForm({ onCancel, onCreated, onSaved, vehicle }: { onCancel: () => void; onCreated?: (vehicle: Vehicle) => void; onSaved?: (vehicle: Vehicle) => void; vehicle?: Vehicle }) {
  const [image, setImage] = useState<File | null>(null)
  const [preview, setPreview] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [createdVehicle, setCreatedVehicle] = useState<Vehicle | null>(null)
  const [removeExistingImage, setRemoveExistingImage] = useState(false)
  const [fuelType, setFuelType] = useState(vehicle?.fuelType ?? 'electric')
  const [vehicleCategory, setVehicleCategory] = useState<string>(vehicle?.vehicleCategory ?? 'van')
  const retainExistingLoadLimits = vehicle?.vehicleCategory === vehicleCategory
  const initialLoadDefaults = vehicle?.loadProfile ? {
    ...vehicleLoadDefaults(vehicle?.vehicleCategory ?? 'van'),
    profileCode: vehicle.loadProfile.profileCode,
    cargoLengthCm: vehicle.loadProfile.cargoLengthCm,
    cargoWidthCm: vehicle.loadProfile.cargoWidthCm,
    cargoHeightCm: vehicle.loadProfile.cargoHeightCm,
  } : vehicleLoadDefaults(vehicle?.vehicleCategory ?? 'van')
  const [loadProfileCode, setLoadProfileCode] = useState(initialLoadDefaults.profileCode)
  const [cargoDimensions, setCargoDimensions] = useState({
    length: initialLoadDefaults.cargoLengthCm,
    width: initialLoadDefaults.cargoWidthCm,
    height: initialLoadDefaults.cargoHeightCm,
  })
  const editing = Boolean(vehicle)
  const complete = (saved: Vehicle) => (onSaved ?? onCreated)?.(saved)

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview)
  }, [preview])

  const selectImage = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null
    setError('')
    if (!file) return
    if (!ACCEPTED_IMAGE_TYPES.has(file.type)) {
      setError('Vehicle image must be JPEG, PNG, or WebP.')
      event.target.value = ''
      return
    }
    if (file.size > MAX_IMAGE_BYTES) {
      setError('Vehicle image must not exceed 5 MB.')
      event.target.value = ''
      return
    }
    if (preview) URL.revokeObjectURL(preview)
    setImage(file)
    setPreview(URL.createObjectURL(file))
  }

  const clearImage = () => {
    if (preview) URL.revokeObjectURL(preview)
    setImage(null)
    setPreview('')
  }

  const uploadSelectedImage = async (vehicle: Vehicle) => {
    if (!image) return vehicle
    return fleetService.uploadVehicleImage(vehicle.id, image)
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    const form = new FormData(event.currentTarget)
    const cargoLengthCm = Number(form.get('cargo_length_cm') || cargoDimensions.length)
    const cargoWidthCm = Number(form.get('cargo_width_cm') || cargoDimensions.width)
    const cargoHeightCm = Number(form.get('cargo_height_cm') || cargoDimensions.height)
    const loadProfile = {
      profile_code: String(form.get('load_profile_code') || loadProfileCode),
      capacity_m3: calculatedCargoVolume(cargoLengthCm, cargoWidthCm, cargoHeightCm),
      cargo_length_cm: cargoLengthCm,
      cargo_width_cm: cargoWidthCm,
      cargo_height_cm: cargoHeightCm,
      max_parcels: Number(form.get('max_parcels') || 120),
      max_stack_layers: Number(form.get('max_stack_layers') || 4),
      vehicle_max_stack_weight_kg: Number(form.get('vehicle_max_stack_weight_kg') || 750),
      is_refrigerated: form.has('is_refrigerated'),
      temp_min_celsius: form.has('is_refrigerated') ? Number(form.get('vehicle_temp_min_celsius')) : undefined,
      temp_max_celsius: form.has('is_refrigerated') ? Number(form.get('vehicle_temp_max_celsius')) : undefined,
      is_hazmat_certified: form.has('is_hazmat_certified'), has_tail_lift: form.has('has_tail_lift'),
      available_from: String(form.get('available_from') || '08:00'), available_until: String(form.get('available_until') || '17:00'),
    }
    try {
      let saved = editing && vehicle
        ? await fleetService.updateVehicle(vehicle.id, {
          vehicle_code: String(form.get('vehicle_code') || '').trim(),
          registration_number: String(form.get('registration_number') || '').trim(),
          vehicle_type: `${String(form.get('fuel_type') || 'electric')}_${String(form.get('vehicle_category') || 'van')}`,
          vehicle_category: String(form.get('vehicle_category') || 'van'),
          fuel_type: String(form.get('fuel_type') || 'electric'),
          in_service_date: String(form.get('in_service_date') || ''),
          payload_capacity_kg: Number(form.get('payload_capacity_kg') || 0),
          brand: String(form.get('brand') || '').trim(),
          model: String(form.get('model') || '').trim(),
          year: Number(form.get('year')),
          current_mileage: Number(form.get('current_mileage') || 0),
          battery_capacity_kwh: fuelType === 'electric' || fuelType === 'hybrid' ? Number(form.get('battery_capacity_kwh') || 0) : undefined,
          onboarding_type: String(form.get('onboarding_type') || vehicle.onboardingType || 'existing_fleet') as 'brand_new' | 'existing_fleet',
          load_profile: loadProfile,
        })
        : await fleetService.createVehicle({
        vehicle_code: String(form.get('vehicle_code') || '').trim(),
        registration_number: String(form.get('registration_number') || '').trim(),
        vehicle_type: `${String(form.get('fuel_type') || 'electric')}_${String(form.get('vehicle_category') || 'van')}`,
        vehicle_category: String(form.get('vehicle_category') || 'van'),
        fuel_type: String(form.get('fuel_type') || 'electric'),
        in_service_date: String(form.get('in_service_date') || ''),
        payload_capacity_kg: Number(form.get('payload_capacity_kg') || 0),
        brand: String(form.get('brand') || '').trim(),
        model: String(form.get('model') || '').trim(),
        year: Number(form.get('year')),
        current_mileage: Number(form.get('current_mileage') || 0),
        battery_capacity_kwh: fuelType === 'electric' || fuelType === 'hybrid' ? Number(form.get('battery_capacity_kwh') || 0) : undefined,
        onboarding_type: String(form.get('onboarding_type') || 'existing_fleet') as 'brand_new' | 'existing_fleet',
        load_profile: loadProfile,
        status: 'inactive',
        health_status: 'unknown',
        } as Parameters<typeof fleetService.createVehicle>[0] & { status: 'inactive'; health_status: 'unknown' })
      setCreatedVehicle(saved)
      try {
        if (editing && vehicle && removeExistingImage && !image) saved = await fleetService.deleteVehicleImage(vehicle.id)
        complete(await uploadSelectedImage(saved))
      } catch (uploadError) {
        setError(`Vehicle created, but the image upload failed. ${uploadError instanceof Error ? uploadError.message : 'Retry the image upload.'}`)
      }
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : 'Unable to create vehicle')
    } finally {
      setSubmitting(false)
    }
  }

  const retryUpload = async () => {
    if (!createdVehicle || !image) return
    setSubmitting(true)
    setError('')
    try {
      complete(await uploadSelectedImage(createdVehicle))
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : 'Unable to upload the vehicle image')
    } finally {
      setSubmitting(false)
    }
  }

  const cancel = () => {
    if (createdVehicle) complete(createdVehicle)
    else onCancel()
  }

  return (
    <ModalViewport>
      <ModalPanel aria-modal="true" className="max-w-4xl" role="dialog">
      <form className="contents" onSubmit={submit}>
        <ModalHeader className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-extrabold text-slate-950">{editing ? 'Edit vehicle' : 'Add vehicle'}</h2>
            <p className="mt-1 text-sm text-slate-500">{editing ? 'Update vehicle identity, specifications, and image.' : 'Register the vehicle for operational review and initial assessment.'}</p>
          </div>
          <button aria-label="Close vehicle form" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100" onClick={cancel} type="button"><X className="h-5 w-5" /></button>
        </ModalHeader>

        <ModalBody className="space-y-7">
          <section>
            <h3 className="text-base font-extrabold text-slate-950">Vehicle identity</h3>
            <div className="mt-4 grid gap-5 lg:grid-cols-[220px_1fr]">
              <div>
                <label className="group grid aspect-[4/3] cursor-pointer place-items-center overflow-hidden rounded-lg border border-dashed border-slate-300 bg-slate-50 text-center hover:border-blue-400 hover:bg-blue-50" htmlFor="vehicle-image">
                  {preview || (vehicle?.imageUrl && !removeExistingImage) ? <img alt="Vehicle upload preview" className="h-full w-full object-cover" src={preview || vehicle?.imageUrl || ''} /> : <span className="px-4 text-sm font-semibold text-slate-500"><ImagePlus className="mx-auto mb-2 h-7 w-7 text-blue-600" />Select vehicle image<span className="mt-1 block text-xs font-normal">JPEG, PNG or WebP · max 5 MB</span></span>}
                </label>
                <input accept="image/jpeg,image/png,image/webp" aria-label="Vehicle image" className="sr-only" id="vehicle-image" onChange={selectImage} type="file" />
                {(image || (vehicle?.imageUrl && !removeExistingImage)) && <button className="mt-2 text-xs font-bold text-red-600" onClick={() => { clearImage(); setRemoveExistingImage(true) }} type="button">Remove image</button>}
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <Field defaultValue={vehicle?.registrationNumber} label="Registration number" name="registration_number" placeholder="WP CAA-1234" required />
                <Field defaultValue={vehicle?.vehicleCode} label="Vehicle code" name="vehicle_code" placeholder="EV-FLEET-001" required />
                <Field defaultValue={vehicle?.brand} label="Brand" name="brand" placeholder="BYD" required />
                <Field defaultValue={vehicle?.modelName} label="Model" name="model" placeholder="T3 Electric Van" required />
                <SelectField defaultValue={vehicleCategory} label="Vehicle category" name="vehicle_category" onChange={(category) => { const defaults = vehicleLoadDefaults(category); setVehicleCategory(category); setLoadProfileCode(defaults.profileCode); setCargoDimensions({ length: defaults.cargoLengthCm, width: defaults.cargoWidthCm, height: defaults.cargoHeightCm }) }} options={VEHICLE_CATEGORIES} />
                <Field defaultValue={vehicle?.year} label="Manufacturing year" name="year" placeholder="2026" required type="number" />
              </div>
            </div>
          </section>

          <section className="border-t border-slate-200 pt-6" key={vehicleCategory}>
            <h3 className="text-base font-extrabold text-slate-950">Load capacity</h3>
            <p className="mt-2 text-sm text-slate-500">Cargo-bay limits are used to build safe parcel loading plans.</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <SelectField defaultValue={loadProfileCode} label="Load profile" name="load_profile_code" onChange={setLoadProfileCode} options={LOAD_PROFILES} />
              <ReadOnlyField label="Calculated cargo volume" value={`${calculatedCargoVolume(cargoDimensions.length, cargoDimensions.width, cargoDimensions.height)} m³`} />
              <Field label="Cargo length (cm)" name="cargo_length_cm" onChange={(value) => setCargoDimensions((current) => ({ ...current, length: Number(value) || 0 }))} placeholder="320" required type="number" value={cargoDimensions.length} />
              <Field label="Cargo width (cm)" name="cargo_width_cm" onChange={(value) => setCargoDimensions((current) => ({ ...current, width: Number(value) || 0 }))} placeholder="170" required type="number" value={cargoDimensions.width} />
              <Field label="Cargo height (cm)" name="cargo_height_cm" onChange={(value) => setCargoDimensions((current) => ({ ...current, height: Number(value) || 0 }))} placeholder="175" required type="number" value={cargoDimensions.height} />
              <Field defaultValue={retainExistingLoadLimits ? vehicle?.loadProfile?.maxParcels : vehicleLoadDefaults(vehicleCategory).maxParcels} label="Maximum parcels" name="max_parcels" placeholder="120" required type="number" />
              <Field defaultValue={retainExistingLoadLimits ? vehicle?.loadProfile?.maxStackLayers : vehicleLoadDefaults(vehicleCategory).maxStackLayers} label="Maximum stack layers" name="max_stack_layers" placeholder="4" required type="number" />
              <Field defaultValue={retainExistingLoadLimits ? vehicle?.loadProfile?.vehicleMaxStackWeightKg : vehicleLoadDefaults(vehicleCategory).maxStackWeightKg} label="Stack weight limit (kg)" name="vehicle_max_stack_weight_kg" placeholder="750" required type="number" />
              <Field defaultValue={vehicle?.loadProfile?.availableFrom ?? '08:00'} label="Available from" name="available_from" placeholder="" required type="time" />
              <Field defaultValue={vehicle?.loadProfile?.availableUntil ?? '17:00'} label="Available until" name="available_until" placeholder="" required type="time" />
            </div>
            <div className="mt-4 flex flex-wrap gap-5"><Check defaultChecked={vehicle?.loadProfile?.isRefrigerated} label="Refrigerated" name="is_refrigerated" /><Check defaultChecked={vehicle?.loadProfile?.isHazmatCertified} label="Hazmat certified" name="is_hazmat_certified" /><Check defaultChecked={vehicle?.loadProfile?.hasTailLift} label="Tail lift" name="has_tail_lift" /></div>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <Field defaultValue={vehicle?.loadProfile?.tempMinCelsius ?? -18} label="Minimum supported temperature (°C)" min={-50} name="vehicle_temp_min_celsius" placeholder="-18" type="number" />
              <Field defaultValue={vehicle?.loadProfile?.tempMaxCelsius ?? 12} label="Maximum supported temperature (°C)" min={-50} name="vehicle_temp_max_celsius" placeholder="12" type="number" />
            </div>
          </section>

          <section className="border-t border-slate-200 pt-6">
            <h3 className="text-base font-extrabold text-slate-950">Fleet specifications</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <SelectField defaultValue={fuelType} label="Fuel type" name="fuel_type" onChange={(value) => setFuelType(value as 'electric' | 'hybrid' | 'diesel' | 'petrol')} options={FUEL_TYPES} />
              <Field defaultValue={vehicle?.inServiceDate} label="In-service date" name="in_service_date" placeholder="" required type="date" />
              <Field defaultValue={vehicle?.payloadCapacityKg} label="Payload capacity (kg)" name="payload_capacity_kg" placeholder="1200" required type="number" />
              {(fuelType === 'electric' || fuelType === 'hybrid') && <Field defaultValue={vehicle?.batteryCapacityKwh} label="Battery capacity (kWh, optional)" name="battery_capacity_kwh" placeholder="80" type="number" />}
              <Field defaultValue={vehicle?.mileage} label="Current mileage (km)" name="current_mileage" placeholder="0" type="number" />
            </div>
          </section>

          <section className="border-t border-slate-200 pt-6">
            <h3 className="text-base font-extrabold text-slate-950">Operational state</h3>
            <p className="mt-2 text-sm text-slate-500">New vehicles remain inactive until their details and initial operational assessment are reviewed.</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              <SelectField defaultValue={vehicle?.onboardingType ?? 'existing_fleet'} label="Vehicle history type" name="onboarding_type" options={ONBOARDING_TYPES} />
              <ReadOnlyField label="Vehicle status" value={editing ? vehicle?.status ?? 'Current status retained' : 'Inactive - review required'} />
              <ReadOnlyField label="Health status" value="Unknown - inspection required" />
            </div>
            <p className="mt-3 text-xs font-medium text-slate-500">Existing fleet vehicles can import completed service history. Brand-new vehicles build history from completed trips and mileage.</p>
          </section>

          {error && <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700" role="alert">{error}</div>}
        </ModalBody>

        <ModalFooter>
          <SecondaryButton onClick={cancel}>Cancel</SecondaryButton>
          {createdVehicle && image ? (
            <PrimaryButton disabled={submitting} onClick={retryUpload}>{submitting ? 'Uploading...' : 'Retry image upload'}</PrimaryButton>
          ) : (
            <PrimaryButton disabled={submitting} type="submit">{submitting ? 'Saving...' : editing ? 'Save changes' : 'Create vehicle'}</PrimaryButton>
          )}
        </ModalFooter>
      </form>
      </ModalPanel>
    </ModalViewport>
  )
}


function Field({ label, name, placeholder, required = false, type = 'text', defaultValue, min, value, onChange }: { label: string; name: string; placeholder: string; required?: boolean; type?: string; defaultValue?: string | number; min?: number; value?: string | number; onChange?: (value: string) => void }) {
  return <label className="text-sm font-bold text-slate-600">{label}<input className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 px-3 font-semibold text-slate-950 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" defaultValue={value === undefined ? defaultValue : undefined} min={type === 'number' ? min ?? 0 : undefined} name={name} onChange={onChange ? (event) => onChange(event.target.value) : undefined} placeholder={placeholder} required={required} type={type} value={value} /></label>
}


function SelectField({ label, name, options, defaultValue, onChange }: { label: string; name: string; options: readonly { value: string; label: string }[]; defaultValue?: string; onChange?: (value: string) => void }) {
  return <label className="text-sm font-bold text-slate-600">{label}<select className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 px-3 font-semibold text-slate-950" defaultValue={defaultValue} name={name} onChange={(event) => onChange?.(event.target.value)} required>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
}


function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return <div><div className="text-sm font-bold text-slate-600">{label}</div><div className="mt-2 flex min-h-11 items-center rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-semibold text-slate-700">{value}</div></div>
}

function Check({ label, name, defaultChecked = false }: { label: string; name: string; defaultChecked?: boolean }) { return <label className="inline-flex items-center gap-2 text-sm font-bold text-slate-700"><input className="h-4 w-4 accent-blue-600" defaultChecked={defaultChecked} name={name} type="checkbox" />{label}</label> }

const VEHICLE_CATEGORIES = [
  { value: 'car', label: 'Car' }, { value: 'van', label: 'Van' },
  { value: 'truck', label: 'Truck' }, { value: 'bus', label: 'Bus' },
] as const

const FUEL_TYPES = [
  { value: 'electric', label: 'Electric' }, { value: 'hybrid', label: 'Hybrid' },
  { value: 'diesel', label: 'Diesel' }, { value: 'petrol', label: 'Petrol' },
] as const

const ONBOARDING_TYPES = [
  { value: 'existing_fleet', label: 'Existing fleet vehicle' },
  { value: 'brand_new', label: 'Brand-new vehicle' },
] as const

const LOAD_PROFILES = [
  { value: 'COMPACT_CAR', label: 'Compact car' }, { value: 'MEDIUM_VAN', label: 'Medium van' },
  { value: 'MEDIUM_VAN_REEFER', label: 'Refrigerated medium van' },
  { value: 'MEDIUM_TRUCK', label: 'Medium truck' }, { value: 'HAZMAT_TRUCK', label: 'Certified hazardous-load truck' },
  { value: 'HEAVY_BUS', label: 'Bus cargo profile' },
] as const

const VEHICLE_LOAD_DEFAULTS: Record<string, { profileCode: string; cargoLengthCm: number; cargoWidthCm: number; cargoHeightCm: number; maxParcels: number; maxStackLayers: number; maxStackWeightKg: number }> = {
  car: { profileCode: 'COMPACT_CAR', cargoLengthCm: 160, cargoWidthCm: 105, cargoHeightCm: 105, maxParcels: 18, maxStackLayers: 2, maxStackWeightKg: 60 },
  van: { profileCode: 'MEDIUM_VAN', cargoLengthCm: 320, cargoWidthCm: 170, cargoHeightCm: 175, maxParcels: 70, maxStackLayers: 4, maxStackWeightKg: 300 },
  truck: { profileCode: 'MEDIUM_TRUCK', cargoLengthCm: 540, cargoWidthCm: 220, cargoHeightCm: 210, maxParcels: 180, maxStackLayers: 6, maxStackWeightKg: 900 },
  bus: { profileCode: 'HEAVY_BUS', cargoLengthCm: 600, cargoWidthCm: 210, cargoHeightCm: 190, maxParcels: 140, maxStackLayers: 5, maxStackWeightKg: 600 },
}

function vehicleLoadDefaults(category: string) { return VEHICLE_LOAD_DEFAULTS[category] ?? VEHICLE_LOAD_DEFAULTS.van }
function calculatedCargoVolume(lengthCm: number, widthCm: number, heightCm: number) { return Math.round((lengthCm * widthCm * heightCm) / 1_000) / 1_000 }
