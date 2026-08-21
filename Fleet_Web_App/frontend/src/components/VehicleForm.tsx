import { ImagePlus, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { VEHICLE_CATEGORIES } from '../data/sriLankaZones'
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
    try {
      let saved = editing && vehicle
        ? await fleetService.updateVehicle(vehicle.id, {
          vehicle_code: String(form.get('vehicle_code') || '').trim(),
          registration_number: String(form.get('registration_number') || '').trim(),
          vehicle_type: String(form.get('vehicle_type') || 'electric_van'),
          brand: String(form.get('brand') || '').trim(),
          model: String(form.get('model') || '').trim(),
          year: Number(form.get('year')),
          current_mileage: Number(form.get('current_mileage') || 0),
          battery_capacity_kwh: Number(form.get('battery_capacity_kwh') || 0),
        })
        : await fleetService.createVehicle({
        vehicle_code: String(form.get('vehicle_code') || '').trim(),
        registration_number: String(form.get('registration_number') || '').trim(),
        vehicle_type: String(form.get('vehicle_type') || 'electric_van'),
        brand: String(form.get('brand') || '').trim(),
        model: String(form.get('model') || '').trim(),
        year: Number(form.get('year')),
        current_mileage: Number(form.get('current_mileage') || 0),
        battery_capacity_kwh: Number(form.get('battery_capacity_kwh') || 0),
        })
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
            <h2 className="text-2xl font-extrabold text-slate-950">{editing ? 'Edit EV vehicle' : 'Add EV vehicle'}</h2>
            <p className="mt-1 text-sm text-slate-500">{editing ? 'Update vehicle identity, specifications, and image.' : 'Register the vehicle, specifications, and operational state.'}</p>
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
                <SelectField defaultValue={vehicle?.type} label="Vehicle category" name="vehicle_type" options={VEHICLE_CATEGORIES} />
                <Field defaultValue={vehicle?.year} label="Manufacturing year" name="year" placeholder="2026" required type="number" />
              </div>
            </div>
          </section>

          <section className="border-t border-slate-200 pt-6">
            <h3 className="text-base font-extrabold text-slate-950">EV specifications</h3>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <ReadOnlyField label="Fuel type" value="Electric" />
              <Field defaultValue={vehicle?.batteryCapacityKwh} label="Battery capacity (kWh)" name="battery_capacity_kwh" placeholder="80" type="number" />
              <Field defaultValue={vehicle?.mileage} label="Current mileage (km)" name="current_mileage" placeholder="0" type="number" />
            </div>
          </section>

          <section className="border-t border-slate-200 pt-6">
            <h3 className="text-base font-extrabold text-slate-950">Operational state</h3>
            <p className="mt-2 text-sm text-slate-500">New EVs start active with unknown health until an inspection or prediction is available.</p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <ReadOnlyField label="Vehicle status" value="Active" />
              <ReadOnlyField label="Health status" value="Unknown - inspection required" />
            </div>
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


function Field({ label, name, placeholder, required = false, type = 'text', defaultValue }: { label: string; name: string; placeholder: string; required?: boolean; type?: string; defaultValue?: string | number }) {
  return <label className="text-sm font-bold text-slate-600">{label}<input className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 px-3 font-semibold text-slate-950 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100" defaultValue={defaultValue} min={type === 'number' ? 0 : undefined} name={name} placeholder={placeholder} required={required} type={type} /></label>
}


function SelectField({ label, name, options, defaultValue }: { label: string; name: string; options: readonly { value: string; label: string }[]; defaultValue?: string }) {
  return <label className="text-sm font-bold text-slate-600">{label}<select className="mt-2 min-h-11 w-full rounded-lg border border-slate-300 px-3 font-semibold text-slate-950" defaultValue={defaultValue} name={name} required>{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
}


function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return <div><div className="text-sm font-bold text-slate-600">{label}</div><div className="mt-2 flex min-h-11 items-center rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-semibold text-slate-700">{value}</div></div>
}
