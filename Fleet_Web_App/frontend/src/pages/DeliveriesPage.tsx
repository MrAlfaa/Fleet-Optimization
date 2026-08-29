import { Ban, CalendarDays, Clock3, Eye, House, MapPin, MapPinned, PackageOpen, Pencil, Plus, SlidersHorizontal, TriangleAlert, Weight, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { FormEvent } from 'react'
import { EmptyState, ErrorState, LoadingState, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { useAsyncData } from '../hooks/useAsyncData'
import { operationsService } from '../services/operationsService'
import { SRI_LANKA_ZONES } from '../data/sriLankaZones'
import { DeliveryLocationPicker } from '../components/DeliveryLocationPicker'
import { nearestSriLankaZone, type LocationPoint } from '../utils/operationalZones'
import { saveRouteDeliverySelection } from '../features/deliveries/routeSelection'
import { DELIVERY_PERIOD_LABELS, updateParcelBatchSelection, type DeliveryPeriod } from '../features/deliveries/parcelBatch'
import { parcelLoadProfileFromForm } from '../features/deliveries/loadProfile'
import type { DeliveryOrder } from '../types'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from '../components/ModalLayout'
import { authService } from '../services/authService'
import { canAccess } from '../utils/permissions'

export function DeliveriesPage() {
  const navigate = useNavigate()
  const currentUser = authService.getSession()
  const canManage = canAccess(currentUser, 'deliveries.manage')
  const canPlan = canAccess(currentUser, 'routes.optimize')
  const [selected, setSelected] = useState<string[]>([])
  const [selectionError, setSelectionError] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [drop, setDrop] = useState<LocationPoint | null>(null)
  const [zoneId, setZoneId] = useState('')
  const [zoneOverridden, setZoneOverridden] = useState(false)
  const [formError, setFormError] = useState('')
  const [zoneFilter, setZoneFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [periodFilter, setPeriodFilter] = useState<'' | DeliveryPeriod>('')
  const [statusFilter, setStatusFilter] = useState('')
  const [planningStatusFilter, setPlanningStatusFilter] = useState('')
  const [sortPriority, setSortPriority] = useState(false)
  const [detailOrder, setDetailOrder] = useState<DeliveryOrder | null>(null)
  const [editingOrder, setEditingOrder] = useState<DeliveryOrder | null>(null)
  const [cancellingOrder, setCancellingOrder] = useState<DeliveryOrder | null>(null)
  const [cancelReason, setCancelReason] = useState('')
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [deliveries, branch] = await Promise.all([
      operationsService.listDeliveries({
        zone_id: zoneFilter || undefined,
        start_date: dateFilter || undefined,
        end_date: dateFilter || undefined,
        delivery_period: periodFilter || undefined,
        load_planning_status: planningStatusFilter || undefined,
      }),
      operationsService.getOperationalBranch(),
    ])
    return { deliveries, branch }
  }, [zoneFilter, dateFilter, periodFilter, planningStatusFilter])

  const deliveries = useMemo(() => data?.deliveries ?? [], [data?.deliveries])
  const branch = data?.branch
  const selectedSet = useMemo(() => new Set(selected), [selected])
  const visibleDeliveries = useMemo(() => {
    const filtered = deliveries.filter((order) => !statusFilter || order.backendStatus === statusFilter)
    if (!sortPriority) return filtered
    const weight = { Critical: 3, High: 2, Standard: 1 }
    return [...filtered].sort((a, b) => weight[b.priority] - weight[a.priority])
  }, [deliveries, sortPriority, statusFilter])
  const firstHalfCount = visibleDeliveries.filter((order) => order.deliveryPeriod === 'first_half').length
  const secondHalfCount = visibleDeliveries.filter((order) => order.deliveryPeriod === 'second_half').length

  const toggle = (order: DeliveryOrder) => {
    const result = updateParcelBatchSelection(selected, order, deliveries)
    setSelected(result.selectedIds)
    setSelectionError(result.error ?? '')
  }

  const createDelivery = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!drop || !zoneId || !branch) {
      setFormError('Select the customer delivery location and confirm its operational zone.')
      return
    }
    setSubmitting(true)
    setFormError('')
    const form = new FormData(event.currentTarget)
    const parcelWeight = optionalFormNumber(form.get('parcel_weight'))
    try {
      const payload: import('../services/operationsService').DeliveryCreatePayload = {
        order_code: String(form.get('order_code') || ''),
        customer_name: String(form.get('customer_name') || ''),
        customer_phone: String(form.get('customer_phone') || ''),
        drop_latitude: drop.latitude,
        drop_longitude: drop.longitude,
        drop_address: String(form.get('drop_address') || ''),
        zone_id: zoneId,
        zone_assignment_method: zoneOverridden ? 'manual_override' : 'confirmed',
        priority: String(form.get('priority') || 'medium'),
        delivery_date: String(form.get('delivery_date') || ''),
        delivery_period: String(form.get('delivery_period') || 'first_half') as DeliveryPeriod,
        ...(parcelWeight === null ? {} : { parcel_weight: parcelWeight }),
        load_profile: parcelLoadProfileFromForm(form),
      }
      if (editingOrder) await operationsService.updateDelivery(editingOrder.id, payload)
      else await operationsService.createDelivery(payload)
      closeForm()
      await reload()
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : 'Unable to save parcel')
    } finally {
      setSubmitting(false)
    }
  }

  const resetCreateForm = () => {
    setDrop(null)
    setZoneId('')
    setZoneOverridden(false)
    setFormError('')
  }
  const closeForm = () => {
    setShowCreate(false)
    setEditingOrder(null)
    resetCreateForm()
  }
  const openCreate = () => {
    setEditingOrder(null)
    resetCreateForm()
    setShowCreate(true)
  }
  const updateDrop = (point: LocationPoint) => {
    setDrop(point)
    setZoneId(nearestSriLankaZone(point).id)
    setZoneOverridden(false)
  }
  const optimizeSelected = () => {
    if (selected.length === 0) return
    saveRouteDeliverySelection(selected)
    navigate('/route-planning')
  }
  const editOrder = (order: DeliveryOrder) => {
    setEditingOrder(order)
    setDrop({ latitude: order.dropLatitude ?? 0, longitude: order.dropLongitude ?? 0 })
    setZoneId(order.zoneId ?? '')
    setZoneOverridden(false)
    setShowCreate(true)
    setDetailOrder(null)
  }

  if (loading) return <LoadingState />
  if (error || !data || !branch) return <ErrorState message={error ?? 'Unable to load parcel operations'} onRetry={reload} />

  return <div>
    <PageHeader
      action={canManage ? <PrimaryButton onClick={openCreate}><Plus className="h-4 w-4" /> Add Parcel</PrimaryButton> : undefined}
      description="Register incoming parcels at the Colombo branch and prepare date-and-period delivery batches."
      title="Parcel Gallery"
    />

    <section className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4" aria-label="Parcel summary">
      <Summary icon={PackageOpen} label="Visible parcels" tone="blue" value={visibleDeliveries.length} />
      <Summary icon={Clock3} label="First Half" tone="emerald" value={firstHalfCount} />
      <Summary icon={Clock3} label="Second Half" tone="amber" value={secondHalfCount} />
      <Summary icon={MapPinned} label="Selected batch" tone="violet" value={selected.length} />
    </section>

    <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-fleet-line bg-white p-4 shadow-card">
      <label className="inline-flex min-w-44 items-center gap-2 rounded-lg border border-fleet-line px-3 py-2 text-sm font-bold"><SlidersHorizontal className="h-4 w-4" /><select aria-label="Filter parcel zone" className="min-w-0 flex-1 bg-transparent outline-none" onChange={(event) => setZoneFilter(event.target.value)} value={zoneFilter}><option value="">All zones</option>{SRI_LANKA_ZONES.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}</select></label>
      <input aria-label="Filter delivery date" className="rounded-lg border border-fleet-line px-3 py-2 text-sm font-bold" onChange={(event) => setDateFilter(event.target.value)} type="date" value={dateFilter} />
      <select aria-label="Filter delivery period" className="rounded-lg border border-fleet-line px-3 py-2 text-sm font-bold" onChange={(event) => setPeriodFilter(event.target.value as '' | DeliveryPeriod)} value={periodFilter}><option value="">Both periods</option><option value="first_half">First Half</option><option value="second_half">Second Half</option></select>
      <select aria-label="Filter parcel status" className="rounded-lg border border-fleet-line px-3 py-2 text-sm font-bold" onChange={(event) => setStatusFilter(event.target.value)} value={statusFilter}><option value="">All statuses</option><option value="pending">Pending</option><option value="assigned">Assigned</option><option value="in_route">In route</option><option value="delivered">Delivered</option><option value="cancelled">Cancelled</option></select>
      <select aria-label="Filter consolidation status" className="rounded-lg border border-fleet-line px-3 py-2 text-sm font-bold" onChange={(event) => setPlanningStatusFilter(event.target.value)} value={planningStatusFilter}><option value="">All planning states</option><option value="unplanned">Not consolidated</option><option value="consolidated">Consolidated</option><option value="reserved">Optimization running</option><option value="planned">Load planned</option><option value="vehicle_assigned">Vehicle assigned</option><option value="routed">Routed</option><option value="failed">Needs planning review</option></select>
      <button className={`rounded-lg border px-3 py-2 text-sm font-bold transition hover:-translate-y-0.5 ${sortPriority ? 'border-blue-300 bg-blue-50 text-blue-700' : 'border-fleet-line hover:bg-slate-50'}`} onClick={() => setSortPriority((value) => !value)} type="button">Priority order</button>
      {canPlan && <button className="ml-auto inline-flex items-center gap-2 rounded-lg bg-blue-100 px-4 py-2 text-sm font-black text-fleet-blue transition hover:-translate-y-0.5 hover:bg-blue-200 disabled:opacity-50" disabled={selected.length === 0} onClick={optimizeSelected} type="button"><MapPinned className="h-4 w-4" />Plan selected ({selected.length})</button>}
    </div>
    {selectionError && <div className="mb-4 flex items-center gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-900"><TriangleAlert className="h-5 w-5 shrink-0" />{selectionError}</div>}

    {visibleDeliveries.length === 0 ? <EmptyState title="No parcels found" description="Register an incoming parcel or adjust the current filters." /> : <section className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-3" aria-label="Parcel gallery">
      {visibleDeliveries.map((order) => <ParcelCard canManage={canManage} canSelect={canPlan} key={order.id} order={order} selected={selectedSet.has(order.id)} onCancel={() => { setCancellingOrder(order); setCancelReason(''); setFormError('') }} onEdit={() => editOrder(order)} onSelect={() => toggle(order)} onView={() => setDetailOrder(order)} />)}
    </section>}

    {showCreate && <ModalViewport><ModalPanel aria-modal="true" className="max-w-5xl" role="dialog"><form className="contents" onSubmit={createDelivery}>
      <ModalHeader><h3 className="text-2xl font-black">{editingOrder ? 'Edit parcel' : 'Register incoming parcel'}</h3><p className="mt-1 text-sm font-semibold text-fleet-muted">The parcel origin is fixed to {branch.name}. Select the delivery date, half, and customer destination.</p></ModalHeader>
      <ModalBody>
        <div className="mb-5 flex items-start gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-emerald-700 text-white"><House className="h-5 w-5" /></span><div className="min-w-0"><div className="font-black text-emerald-950">{branch.name}</div><div className="text-sm font-semibold text-emerald-800">{branch.address}</div><div className="mt-1 text-xs text-emerald-700">Fixed parcel pickup and route origin</div></div></div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Input defaultValue={editingOrder?.orderCode} label="Order code" name="order_code" placeholder="ORD-001" />
          <Input defaultValue={editingOrder?.customer} label="Customer name" name="customer_name" placeholder="Customer name" required />
          <Input defaultValue={editingOrder?.customerPhone} label="Customer phone" name="customer_phone" placeholder="0771234567" />
          <Input defaultValue={editingOrder?.dropAddress} label="Delivery address" name="drop_address" placeholder="Customer delivery address" required />
          <Input defaultValue={editingOrder?.parcelWeight?.toString()} label="Parcel weight (kg)" min="0.01" name="parcel_weight" placeholder="5.5" required type="number" />
          <label className="text-sm font-bold text-fleet-muted">Priority<select className="mt-2 min-h-11 w-full rounded-lg border border-fleet-line px-3 font-semibold" defaultValue={backendPriority(editingOrder)} name="priority"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option></select></label>
          <Input defaultValue={editingOrder?.deliveryDate ?? colomboToday()} label="Delivery date" min={editingOrder ? undefined : colomboToday()} name="delivery_date" placeholder="" required type="date" />
          <label className="text-sm font-bold text-fleet-muted">Delivery period<select className="mt-2 min-h-11 w-full rounded-lg border border-fleet-line px-3 font-semibold" defaultValue={editingOrder?.deliveryPeriod ?? 'first_half'} name="delivery_period" required><option value="first_half">First Half · 08:00–12:00</option><option value="second_half">Second Half · 13:00–17:00</option></select></label>
        </div>
        <section className="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4"><h4 className="font-black text-slate-950">Size and handling</h4><div className="mt-3 grid gap-4 md:grid-cols-3"><Input defaultValue={editingOrder?.loadProfile?.lengthCm.toString()} label="Length (cm)" min="0.01" name="length_cm" placeholder="50" required type="number" /><Input defaultValue={editingOrder?.loadProfile?.widthCm.toString()} label="Width (cm)" min="0.01" name="width_cm" placeholder="40" required type="number" /><Input defaultValue={editingOrder?.loadProfile?.heightCm.toString()} label="Height (cm)" min="0.01" name="height_cm" placeholder="30" required type="number" /><Input defaultValue={editingOrder?.loadProfile?.maxStackWeightKg.toString()} label="Maximum stack weight (kg)" min="0" name="max_stack_weight_kg" placeholder="0" type="number" /><label className="text-sm font-bold text-fleet-muted">Service type<select className="mt-2 min-h-11 w-full rounded-lg border border-fleet-line px-3 font-semibold" defaultValue={editingOrder?.loadProfile?.serviceType ?? 'door_to_door'} name="service_type"><option value="door_to_door">Door to door</option><option value="collection_point">Collection point</option><option value="locker_drop">Locker drop</option><option value="standard">Standard</option></select></label></div><div className="mt-4 flex flex-wrap gap-4"><HandlingCheck checked={editingOrder?.loadProfile?.fragile} label="Fragile" name="fragile" /><HandlingCheck checked={editingOrder?.loadProfile?.stackable ?? true} label="Stackable" name="stackable" /><HandlingCheck checked={editingOrder?.loadProfile?.loadingOrientationFixed} label="Fixed orientation" name="loading_orientation_fixed" /><HandlingCheck checked={editingOrder?.loadProfile?.doNotTilt} label="Do not tilt" name="do_not_tilt" /><HandlingCheck checked={editingOrder?.loadProfile?.twoPersonLift} label="Two-person lift" name="two_person_lift" /><HandlingCheck checked={editingOrder?.loadProfile?.hazardous} label="Hazardous" name="hazardous" /><HandlingCheck checked={editingOrder?.loadProfile?.requiresRefrigeration} label="Refrigerated" name="requires_refrigeration" /></div><div className="mt-4 grid gap-4 md:grid-cols-3"><Input defaultValue={editingOrder?.loadProfile?.hazmatClass ?? ''} label="Hazmat class" name="hazmat_class" placeholder="Required if hazardous" /><Input defaultValue={editingOrder?.loadProfile?.tempMinCelsius?.toString()} label="Minimum temperature (°C)" name="temp_min_celsius" placeholder="2" type="number" /><Input defaultValue={editingOrder?.loadProfile?.tempMaxCelsius?.toString()} label="Maximum temperature (°C)" name="temp_max_celsius" placeholder="8" type="number" /></div></section>
        <div className="mt-5"><DeliveryLocationPicker branch={branch} drop={drop} onDropChange={updateDrop} /></div>
        <div className="mt-4 grid gap-4 md:grid-cols-[1fr_auto] md:items-end"><label className="text-sm font-bold text-fleet-muted">Operational zone<select className="mt-2 min-h-11 w-full rounded-lg border border-fleet-line px-3 font-semibold" onChange={(event) => { setZoneId(event.target.value); setZoneOverridden(event.target.value !== nearestSriLankaZone(drop ?? { latitude: branch.latitude, longitude: branch.longitude }).id) }} value={zoneId}><option value="">Select delivery location first</option>{SRI_LANKA_ZONES.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}</select></label>{drop && zoneId && <div className={`rounded-lg px-3 py-2 text-xs font-bold ${nearestSriLankaZone(drop).distanceKm <= 35 ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-800'}`}>{nearestSriLankaZone(drop).distanceKm.toFixed(1)} km from nearest zone centre</div>}</div>
        {drop && nearestSriLankaZone(drop).distanceKm > 35 && <div className="mt-3 flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-800"><TriangleAlert className="h-5 w-5 shrink-0" />This destination is outside the configured 35 km service radius. Confirm the operational zone before saving.</div>}
        {formError && <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{formError}</div>}
      </ModalBody>
      <ModalFooter><SecondaryButton onClick={closeForm}>Cancel</SecondaryButton><PrimaryButton disabled={submitting || !drop || !zoneId} type="submit">{submitting ? 'Saving...' : editingOrder ? 'Save changes' : 'Register parcel'}</PrimaryButton></ModalFooter>
    </form></ModalPanel></ModalViewport>}

    {detailOrder && <ModalViewport align="right"><ModalPanel aria-modal="true" className="h-full max-w-lg" role="dialog"><ModalHeader className="flex items-start justify-between"><div><h2 className="text-xl font-black">{detailOrder.orderCode}</h2><p className="text-sm text-slate-500">{detailOrder.customer}</p></div><button aria-label="Close parcel details" className="rounded-lg p-2 hover:bg-slate-100" onClick={() => setDetailOrder(null)} type="button"><X /></button></ModalHeader><ModalBody><dl className="grid grid-cols-2 gap-3"><Detail label="Status" value={detailOrder.backendStatus} /><Detail label="Planning state" value={planningStatusLabel(detailOrder.loadPlanningStatus)} /><Detail label="Consolidation ID" value={detailOrder.activeConsolidationId || 'Not consolidated'} /><Detail label="Priority" value={detailOrder.priority} /><Detail label="Delivery date" value={detailOrder.deliveryDate} /><Detail label="Delivery period" value={periodLabel(detailOrder.deliveryPeriod)} /><Detail label="Zone" value={detailOrder.zone} /><Detail label="Branch origin" value={branch.name} /><Detail label="Destination" value={detailOrder.dropAddress || `${detailOrder.dropLatitude}, ${detailOrder.dropLongitude}`} /><Detail label="Parcel weight" value={formatParcelWeight(detailOrder.parcelWeight)} /><Detail label="Parcel volume" value={detailOrder.loadProfile ? `${detailOrder.loadProfile.volumeM3.toFixed(4)} m³` : 'Not recorded'} /><Detail label="Vehicle" value={detailOrder.assignedVehicleId || 'Assigned during dispatch'} /><Detail label="Driver" value={detailOrder.assignedDriverId || 'Assigned during dispatch'} /></dl></ModalBody><ModalFooter>{canManage && <SecondaryButton disabled={detailOrder.backendStatus !== 'pending'} onClick={() => editOrder(detailOrder)}><Pencil className="h-4 w-4" />Edit parcel</SecondaryButton>}{canPlan && detailOrder.backendStatus === 'pending' && ['unplanned', 'failed'].includes(detailOrder.loadPlanningStatus ?? 'unplanned') && <PrimaryButton onClick={() => { toggle(detailOrder); setDetailOrder(null) }}><MapPinned className="h-4 w-4" />{selectedSet.has(detailOrder.id) ? 'Remove from batch' : 'Select for route'}</PrimaryButton>}</ModalFooter></ModalPanel></ModalViewport>}

    {cancellingOrder && <ModalViewport><ModalPanel aria-modal="true" className="max-w-md" role="dialog"><form className="contents" onSubmit={async (event) => { event.preventDefault(); if (!cancelReason.trim()) return; setSubmitting(true); try { await operationsService.cancelDelivery(cancellingOrder.id, cancelReason.trim()); setSelected((items) => items.filter((id) => id !== cancellingOrder.id)); setCancellingOrder(null); setCancelReason(''); await reload() } catch (cancelError) { setFormError(cancelError instanceof Error ? cancelError.message : 'Unable to cancel parcel') } finally { setSubmitting(false) } }}><ModalHeader><h3 className="text-xl font-black">Cancel {cancellingOrder.orderCode}</h3><p className="mt-2 text-sm font-semibold text-fleet-muted">The parcel remains in operational history and is removed from demand and route planning.</p></ModalHeader><ModalBody><label className="block text-sm font-bold text-fleet-muted">Cancellation reason<textarea autoFocus className="mt-2 min-h-28 w-full resize-y rounded-lg border border-fleet-line p-3 font-semibold outline-none focus:ring-4 focus:ring-red-100" onChange={(event) => setCancelReason(event.target.value)} placeholder="Explain why this parcel is being cancelled" required value={cancelReason} /></label>{formError && <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{formError}</div>}</ModalBody><ModalFooter><SecondaryButton onClick={() => { setCancellingOrder(null); setCancelReason(''); setFormError('') }}>Keep parcel</SecondaryButton><button className="rounded-lg bg-red-600 px-4 py-2 text-sm font-black text-white transition hover:bg-red-700 disabled:opacity-50" disabled={submitting || !cancelReason.trim()} type="submit">{submitting ? 'Cancelling...' : 'Cancel parcel'}</button></ModalFooter></form></ModalPanel></ModalViewport>}
  </div>
}

function ParcelCard({ order, selected, onCancel, onEdit, onSelect, onView, canManage, canSelect }: { order: DeliveryOrder; selected: boolean; onCancel: () => void; onEdit: () => void; onSelect: () => void; onView: () => void; canManage: boolean; canSelect: boolean }) {
  const pending = order.backendStatus === 'pending' && ['unplanned', 'failed'].includes(order.loadPlanningStatus ?? 'unplanned')
  return <article className={`min-w-0 rounded-lg border bg-white p-4 shadow-card transition hover:-translate-y-0.5 hover:shadow-lg ${selected ? 'border-blue-400 ring-2 ring-blue-100' : 'border-fleet-line'}`}>
    <div className="flex items-start justify-between gap-3"><div className="min-w-0"><div className="truncate text-lg font-black text-fleet-ink">{order.orderCode}</div><div className="truncate text-sm font-semibold text-fleet-muted">{order.customer}</div></div>{canSelect && <input aria-label={`Select ${order.orderCode} for route`} checked={selected} className="mt-1 h-4 w-4 accent-blue-600" disabled={!pending} onChange={onSelect} type="checkbox" />}</div>
    <div className="mt-4 flex flex-wrap gap-2"><StatusBadge tone={order.priority === 'Critical' ? 'red' : order.priority === 'High' ? 'amber' : 'slate'}>{order.priority}</StatusBadge><StatusBadge tone={order.status === 'Routed' ? 'green' : order.status === 'In Transit' ? 'blue' : 'slate'}>{order.status}</StatusBadge>{order.loadPlanningStatus && order.loadPlanningStatus !== 'unplanned' && <StatusBadge tone={order.loadPlanningStatus === 'consolidated' ? 'blue' : order.loadPlanningStatus === 'routed' ? 'green' : 'amber'}>{planningStatusLabel(order.loadPlanningStatus)}</StatusBadge>}</div>
    <dl className="mt-4 grid gap-2 text-sm"><CardDetail icon={CalendarDays} label="Delivery" value={order.deliveryDate || 'Not scheduled'} /><CardDetail icon={Clock3} label="Period" value={periodLabel(order.deliveryPeriod)} /><CardDetail icon={MapPin} label="Zone" value={order.zone} /><CardDetail icon={Weight} label="Weight" value={formatParcelWeight(order.parcelWeight)} /></dl>
    <div className="mt-4 flex justify-end gap-1 border-t border-fleet-line pt-3"><ActionButton label="View parcel" onClick={onView}><Eye className="h-4 w-4" /></ActionButton>{canManage && <><ActionButton disabled={!pending || Boolean(order.assignedDriverId || order.assignedVehicleId)} label="Edit parcel" onClick={onEdit}><Pencil className="h-4 w-4" /></ActionButton><ActionButton danger disabled={['delivered', 'in_route', 'cancelled'].includes(order.backendStatus ?? '')} label="Cancel parcel" onClick={onCancel}><Ban className="h-4 w-4" /></ActionButton></>}</div>
  </article>
}

function Summary({ icon: Icon, label, tone, value }: { icon: typeof PackageOpen; label: string; tone: 'blue' | 'emerald' | 'amber' | 'violet'; value: number }) {
  const tones = { blue: 'bg-blue-50 text-blue-700', emerald: 'bg-emerald-50 text-emerald-700', amber: 'bg-amber-50 text-amber-700', violet: 'bg-violet-50 text-violet-700' }
  return <div className="flex items-center gap-3 rounded-lg border border-fleet-line bg-white p-4 shadow-card"><span className={`grid h-10 w-10 place-items-center rounded-lg ${tones[tone]}`}><Icon className="h-5 w-5" /></span><div><div className="text-xs font-bold uppercase text-fleet-muted">{label}</div><div className="text-2xl font-black text-fleet-ink">{value}</div></div></div>
}

function CardDetail({ icon: Icon, label, value }: { icon: typeof CalendarDays; label: string; value: string }) { return <div className="flex min-w-0 items-center gap-2"><Icon className="h-4 w-4 shrink-0 text-fleet-blue" /><dt className="w-16 shrink-0 font-semibold text-fleet-muted">{label}</dt><dd className="truncate font-bold text-fleet-ink">{value}</dd></div> }
function ActionButton({ children, danger = false, disabled = false, label, onClick }: { children: React.ReactNode; danger?: boolean; disabled?: boolean; label: string; onClick: () => void }) { return <button aria-label={label} className={`rounded-lg p-2 transition hover:-translate-y-0.5 disabled:opacity-35 ${danger ? 'text-red-700 hover:bg-red-50' : 'text-fleet-muted hover:bg-blue-50 hover:text-blue-700'}`} disabled={disabled} onClick={onClick} title={label} type="button">{children}</button> }
function Input({ defaultValue, label, min, name, placeholder, required = false, type = 'text' }: { defaultValue?: string; label: string; min?: string; name: string; placeholder: string; required?: boolean; type?: string }) { return <label className="text-sm font-bold text-fleet-muted">{label}<input className="mt-2 min-h-11 w-full rounded-lg border border-fleet-line px-3 font-semibold outline-none focus:ring-4 focus:ring-blue-100" defaultValue={defaultValue} min={min} name={name} placeholder={placeholder} required={required} step="any" type={type} /></label> }
function HandlingCheck({ checked = false, label, name }: { checked?: boolean; label: string; name: string }) { return <label className="inline-flex items-center gap-2 text-sm font-bold text-slate-700"><input className="h-4 w-4 accent-blue-600" defaultChecked={checked} name={name} type="checkbox" />{label}</label> }
function Detail({ label, value }: { label: string; value?: string | null }) { return <div className="min-w-0 rounded-lg border border-slate-200 p-3"><dt className="text-xs font-bold text-slate-500">{label}</dt><dd className="mt-1 break-words text-sm font-bold capitalize">{value || 'Not assigned'}</dd></div> }
function periodLabel(period?: DeliveryPeriod) { return period ? DELIVERY_PERIOD_LABELS[period] : 'Not scheduled' }
function formatParcelWeight(weight?: number | null) { return weight == null ? 'Not recorded' : `${new Intl.NumberFormat('en-LK', { maximumFractionDigits: 2 }).format(weight)} kg` }
function optionalFormNumber(value: FormDataEntryValue | null) { const text = String(value ?? '').trim(); if (!text) return null; const number = Number(text); return Number.isFinite(number) ? number : null }
function backendPriority(order: DeliveryOrder | null) { return order?.priority === 'Critical' ? 'urgent' : order?.priority === 'High' ? 'high' : 'medium' }
function planningStatusLabel(value?: string) { return ({ unplanned: 'Not consolidated', consolidated: 'Consolidated', reserved: 'Optimization running', planned: 'Load planned', vehicle_assigned: 'Vehicle assigned', routed: 'Routed', failed: 'Planning review' } as Record<string, string>)[value ?? 'unplanned'] ?? value ?? 'Not consolidated' }
function colomboToday() { return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Colombo', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date()) }
