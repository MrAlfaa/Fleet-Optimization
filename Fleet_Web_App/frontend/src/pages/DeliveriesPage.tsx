import { Ban, Eye, MapPinned, Pencil, Plus, SlidersHorizontal, TriangleAlert, Warehouse, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import type { FormEvent } from 'react'
import { DataTable, EmptyState, ErrorState, LoadingState, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { useAsyncData } from '../hooks/useAsyncData'
import { operationsService } from '../services/operationsService'
import { SRI_LANKA_ZONES } from '../data/sriLankaZones'
import { DeliveryLocationPicker } from '../components/DeliveryLocationPicker'
import { nearestSriLankaZone, type LocationPoint } from '../utils/operationalZones'
import { saveRouteDeliverySelection } from '../features/deliveries/routeSelection'
import type { DeliveryOrder } from '../types'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from '../components/ModalLayout'

export function DeliveriesPage() {
  const navigate = useNavigate()
  const [selected, setSelected] = useState<string[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [pickup, setPickup] = useState<LocationPoint | null>(null)
  const [drop, setDrop] = useState<LocationPoint | null>(null)
  const [locationMode, setLocationMode] = useState<'pickup' | 'drop'>('pickup')
  const [zoneId, setZoneId] = useState('')
  const [zoneOverridden, setZoneOverridden] = useState(false)
  const [formError, setFormError] = useState('')
  const [zoneFilter, setZoneFilter] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sortPriority, setSortPriority] = useState(false)
  const [detailOrder, setDetailOrder] = useState<DeliveryOrder | null>(null)
  const [editingOrder, setEditingOrder] = useState<DeliveryOrder | null>(null)
  const [cancellingOrder, setCancellingOrder] = useState<DeliveryOrder | null>(null)
  const [cancelReason, setCancelReason] = useState('')
  const { data: deliveries, error, loading, reload } = useAsyncData(() => operationsService.listDeliveries({ zone_id: zoneFilter || undefined, start_date: dateFilter || undefined, end_date: dateFilter || undefined }), [zoneFilter, dateFilter])
  const selectedCount = selected.length
  const selectedSet = useMemo(() => new Set(selected), [selected])
  const visibleDeliveries = useMemo(() => {
    const filtered = (deliveries ?? []).filter((order) => !statusFilter || order.backendStatus === statusFilter)
    if (!sortPriority) return filtered
    const weight = { Critical: 3, High: 2, Standard: 1 }
    return [...filtered].sort((a, b) => weight[b.priority] - weight[a.priority])
  }, [deliveries, sortPriority, statusFilter])
  const toggle = (id: string) => setSelected((items) => (items.includes(id) ? items.filter((item) => item !== id) : [...items, id]))

  const createDelivery = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!pickup || !drop || !zoneId) {
      setFormError('Select pickup and drop locations, then confirm the suggested Sri Lankan zone.')
      return
    }
    setSubmitting(true)
    setFormError('')
    const form = new FormData(event.currentTarget)
    try {
      const payload: import('../services/operationsService').DeliveryCreatePayload = {
        order_code: String(form.get('order_code') || ''),
        customer_name: String(form.get('customer_name') || ''),
        pickup_latitude: pickup.latitude,
        pickup_longitude: pickup.longitude,
        drop_latitude: drop.latitude,
        drop_longitude: drop.longitude,
        pickup_address: String(form.get('pickup_address') || ''),
        drop_address: String(form.get('drop_address') || ''),
        zone_id: zoneId,
        zone_assignment_method: zoneOverridden ? 'manual_override' : 'confirmed',
        priority: String(form.get('priority') || 'medium'),
        scheduled_date: String(form.get('scheduled_date') || '') || undefined,
      }
      if (editingOrder) await operationsService.updateDelivery(editingOrder.id, payload)
      else await operationsService.createDelivery(payload)
      setShowCreate(false)
      setEditingOrder(null)
      resetCreateForm()
      await reload()
    } catch (reason) {
      setFormError(reason instanceof Error ? reason.message : 'Unable to create delivery order')
    } finally {
      setSubmitting(false)
    }
  }

  const resetCreateForm = () => {
    setPickup(null)
    setDrop(null)
    setLocationMode('pickup')
    setZoneId('')
    setZoneOverridden(false)
    setFormError('')
  }

  const updateDrop = (point: LocationPoint) => {
    setDrop(point)
    const nearest = nearestSriLankaZone(point)
    setZoneId(nearest.id)
    setZoneOverridden(false)
  }

  const useColomboDepot = () => {
    setPickup({ latitude: 6.9271, longitude: 79.8612 })
    setLocationMode('drop')
  }

  const optimizeSelected = () => {
    if (selected.length === 0) return
    saveRouteDeliverySelection(selected)
    navigate('/route-planning')
  }

  const editOrder = (order: DeliveryOrder) => { setEditingOrder(order); setPickup({ latitude: order.pickupLatitude ?? 0, longitude: order.pickupLongitude ?? 0 }); setDrop({ latitude: order.dropLatitude ?? 0, longitude: order.dropLongitude ?? 0 }); setZoneId(order.zoneId ?? ''); setShowCreate(true); setDetailOrder(null) }

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={reload} />

  return (
    <div>
      <PageHeader
        action={<PrimaryButton onClick={() => setShowCreate(true)}><Plus className="h-4 w-4" /> Add Delivery Point</PrimaryButton>}
        description="Manage and route incoming delivery orders across active zones."
        title="Delivery Management"
      />
      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-2xl border border-fleet-line bg-white p-4 shadow-card">
        <label className="inline-flex items-center gap-2 rounded-xl border border-fleet-line px-3 py-2 text-sm font-bold"><SlidersHorizontal className="h-4 w-4" /><select aria-label="Filter delivery zone" className="bg-transparent outline-none" onChange={(event) => setZoneFilter(event.target.value)} value={zoneFilter}><option value="">All zones</option>{SRI_LANKA_ZONES.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}</select></label>
        <input aria-label="Filter scheduled date" className="rounded-xl border border-fleet-line px-3 py-2 text-sm font-bold" onChange={(event) => setDateFilter(event.target.value)} type="date" value={dateFilter} />
        <select aria-label="Filter delivery status" className="rounded-xl border border-fleet-line px-3 py-2 text-sm font-bold" onChange={(event) => setStatusFilter(event.target.value)} value={statusFilter}><option value="">All statuses</option><option value="pending">Pending</option><option value="assigned">Assigned</option><option value="in_route">In route</option><option value="delivered">Delivered</option><option value="cancelled">Cancelled</option></select>
        <button className={`rounded-xl border px-3 py-2 text-sm font-bold ${sortPriority ? 'border-blue-300 bg-blue-50 text-blue-700' : 'border-fleet-line'}`} onClick={() => setSortPriority((value) => !value)} type="button">Sort by Priority</button>
        <div className="ml-auto text-sm font-black text-fleet-blue">Route Selected ({selectedCount})</div>
        <button className="inline-flex items-center gap-2 rounded-xl bg-blue-100 px-4 py-2 text-sm font-black text-fleet-blue disabled:opacity-50" disabled={selectedCount === 0} onClick={optimizeSelected} type="button">
          <MapPinned className="h-4 w-4" /> Optimize
        </button>
      </div>
      {!deliveries || deliveries.length === 0 ? (
        <EmptyState title="No delivery orders" description="Create delivery orders before optimizing a route." />
      ) : (
        <DataTable headers={['', 'Customer / Ref', 'Priority', 'Time Window', 'Zone', 'Location', 'Status', 'Actions']}>
          {visibleDeliveries.map((order) => (
            <tr className={selectedSet.has(order.id) ? 'bg-blue-50' : 'hover:bg-blue-50/40'} key={order.id}>
              <td className="px-5 py-4"><input checked={selectedSet.has(order.id)} onChange={() => toggle(order.id)} type="checkbox" /></td>
              <td className="px-5 py-4"><div className="font-black">{order.customer}</div><div className="text-xs font-bold text-fleet-muted">{order.orderCode}</div></td>
              <td className="px-5 py-4"><StatusBadge tone={order.priority === 'Critical' ? 'red' : order.priority === 'High' ? 'amber' : 'slate'}>{order.priority}</StatusBadge></td>
              <td className="px-5 py-4 font-semibold">{order.timeWindow}</td>
              <td className="px-5 py-4"><StatusBadge tone="slate">{order.zone}</StatusBadge></td>
              <td className="px-5 py-4 text-fleet-muted">{order.location}</td>
              <td className="px-5 py-4"><StatusBadge tone={order.status === 'Routed' ? 'green' : order.status === 'In Transit' ? 'blue' : 'slate'}>{order.status}</StatusBadge></td>
              <td className="px-5 py-4"><div className="flex gap-1"><button aria-label={`View ${order.orderCode}`} className="rounded-lg p-2 transition hover:-translate-y-0.5 hover:bg-blue-50 hover:text-blue-700" onClick={() => setDetailOrder(order)} title="View delivery details" type="button"><Eye className="h-4 w-4" /></button><button aria-label={`Edit ${order.orderCode}`} className="rounded-lg p-2 transition hover:-translate-y-0.5 hover:bg-blue-50 hover:text-blue-700 disabled:opacity-40" disabled={order.backendStatus !== 'pending' || Boolean(order.assignedDriverId || order.assignedVehicleId)} onClick={() => editOrder(order)} title="Edit delivery" type="button"><Pencil className="h-4 w-4" /></button><button aria-label={`Cancel ${order.orderCode}`} className="rounded-lg p-2 text-red-700 transition hover:-translate-y-0.5 hover:bg-red-50 disabled:opacity-40" disabled={['delivered','in_route','cancelled'].includes(order.backendStatus ?? '')} onClick={() => { setCancellingOrder(order); setCancelReason(''); setFormError('') }} title="Cancel delivery" type="button"><Ban className="h-4 w-4" /></button></div></td>
            </tr>
          ))}
        </DataTable>
      )}

      {showCreate && (
        <ModalViewport>
          <ModalPanel aria-modal="true" className="max-w-5xl" role="dialog">
          <form className="contents" onSubmit={createDelivery}>
            <ModalHeader>
              <h3 className="text-2xl font-black">{editingOrder ? 'Edit delivery order' : 'Add delivery order'}</h3>
              <p className="mt-1 text-sm font-semibold text-fleet-muted">Select pickup and delivery locations, then confirm the suggested operational zone.</p>
            </ModalHeader>
            <ModalBody>
            <div className="grid gap-4 md:grid-cols-2">
              <Input defaultValue={editingOrder?.orderCode} label="Order code" name="order_code" placeholder="ORD-WEB-001" />
              <Input defaultValue={editingOrder?.customer} label="Customer" name="customer_name" placeholder="Customer name" />
              <Input defaultValue={editingOrder?.pickupAddress} label="Pickup address (optional)" name="pickup_address" placeholder="Depot or collection address" />
              <Input defaultValue={editingOrder?.dropAddress} label="Drop address" name="drop_address" placeholder="Delivery address" />
              <label className="text-sm font-bold text-fleet-muted">Priority<select className="mt-2 min-h-11 w-full rounded-xl border border-fleet-line px-3 font-semibold" defaultValue="medium" name="priority"><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="urgent">Urgent</option></select></label>
              <Input label="Scheduled date" name="scheduled_date" placeholder="" type="datetime-local" />
            </div>
            <div className="my-4 flex justify-end"><button className="inline-flex items-center gap-2 rounded-lg border border-fleet-line bg-slate-50 px-3 py-2 text-xs font-bold text-fleet-blue" onClick={useColomboDepot} type="button"><Warehouse className="h-4 w-4" />Use Colombo Depot as pickup</button></div>
            <DeliveryLocationPicker drop={drop} mode={locationMode} onDropChange={updateDrop} onModeChange={setLocationMode} onPickupChange={(point) => { setPickup(point); setLocationMode('drop') }} pickup={pickup} />
            <div className="mt-4 grid gap-4 md:grid-cols-[1fr_auto] md:items-end">
              <label className="text-sm font-bold text-fleet-muted">Suggested operational zone<select className="mt-2 min-h-11 w-full rounded-xl border border-fleet-line px-3 font-semibold" onChange={(event) => { setZoneId(event.target.value); setZoneOverridden(event.target.value !== nearestSriLankaZone(drop ?? { latitude: 6.9271, longitude: 79.8612 }).id) }} value={zoneId}><option value="">Select drop location first</option>{SRI_LANKA_ZONES.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}</select></label>
              {drop && zoneId && <div className={`rounded-lg px-3 py-2 text-xs font-bold ${nearestSriLankaZone(drop).distanceKm <= 35 ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-800'}`}>{nearestSriLankaZone(drop).distanceKm.toFixed(1)} km from nearest zone center</div>}
            </div>
            {drop && nearestSriLankaZone(drop).distanceKm > 35 && <div className="mt-3 flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-800"><TriangleAlert className="h-5 w-5 shrink-0" />This drop point is outside the configured 35 km service radius. Confirm the zone before creating the order.</div>}
            {formError && <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{formError}</div>}
            </ModalBody>
            <ModalFooter>
              <SecondaryButton onClick={() => { setShowCreate(false); resetCreateForm() }}>Cancel</SecondaryButton>
              <PrimaryButton disabled={submitting || !pickup || !drop || !zoneId} type="submit">{submitting ? 'Saving...' : editingOrder ? 'Save changes' : 'Create delivery'}</PrimaryButton>
            </ModalFooter>
          </form>
          </ModalPanel>
        </ModalViewport>
      )}
      {detailOrder && <ModalViewport align="right"><ModalPanel aria-modal="true" className="h-full max-w-lg" role="dialog"><ModalHeader className="flex items-start justify-between"><div><h2 className="text-xl font-black">{detailOrder.orderCode}</h2><p className="text-sm text-slate-500">{detailOrder.customer}</p></div><button aria-label="Close delivery detail" onClick={() => setDetailOrder(null)} type="button"><X /></button></ModalHeader><ModalBody><dl className="grid grid-cols-2 gap-3"><Detail label="Status" value={detailOrder.backendStatus} /><Detail label="Priority" value={detailOrder.priority} /><Detail label="Zone" value={detailOrder.zone} /><Detail label="Schedule" value={detailOrder.timeWindow} /><Detail label="Pickup" value={detailOrder.pickupAddress || `${detailOrder.pickupLatitude}, ${detailOrder.pickupLongitude}`} /><Detail label="Drop" value={detailOrder.dropAddress || `${detailOrder.dropLatitude}, ${detailOrder.dropLongitude}`} /><Detail label="Vehicle" value={detailOrder.assignedVehicleId || 'Assigned during dispatch'} /><Detail label="Driver" value={detailOrder.assignedDriverId || 'Assigned during dispatch'} /></dl></ModalBody><ModalFooter><SecondaryButton disabled={detailOrder.backendStatus !== 'pending'} onClick={() => editOrder(detailOrder)}><Pencil className="h-4 w-4" />Edit order</SecondaryButton>{detailOrder.backendStatus === 'pending' && <PrimaryButton onClick={() => { toggle(detailOrder.id); setDetailOrder(null) }}><MapPinned className="h-4 w-4" />{selectedSet.has(detailOrder.id) ? 'Remove from route' : 'Select for route'}</PrimaryButton>}</ModalFooter></ModalPanel></ModalViewport>}
      {cancellingOrder && <ModalViewport><ModalPanel aria-modal="true" className="max-w-md" role="dialog"><form className="contents" onSubmit={async (event) => { event.preventDefault(); if (!cancelReason.trim()) return; setSubmitting(true); try { await operationsService.cancelDelivery(cancellingOrder.id, cancelReason.trim()); setSelected((items) => items.filter((id) => id !== cancellingOrder.id)); setCancellingOrder(null); setCancelReason(''); await reload() } catch (cancelError) { setFormError(cancelError instanceof Error ? cancelError.message : 'Unable to cancel delivery') } finally { setSubmitting(false) } }}><ModalHeader><h3 className="text-xl font-black">Cancel {cancellingOrder.orderCode}</h3><p className="mt-2 text-sm font-semibold text-fleet-muted">The order remains in operational history and is removed from demand and route planning.</p></ModalHeader><ModalBody><label className="block text-sm font-bold text-fleet-muted">Cancellation reason<textarea autoFocus className="mt-2 min-h-28 w-full resize-y rounded-xl border border-fleet-line p-3 font-semibold outline-none focus:ring-4 focus:ring-red-100" onChange={(event) => setCancelReason(event.target.value)} placeholder="Explain why this order is being cancelled" required value={cancelReason} /></label>{formError && <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{formError}</div>}</ModalBody><ModalFooter><SecondaryButton onClick={() => { setCancellingOrder(null); setCancelReason(''); setFormError('') }}>Keep order</SecondaryButton><button className="rounded-xl bg-red-600 px-4 py-2 text-sm font-black text-white disabled:opacity-50" disabled={submitting || !cancelReason.trim()} type="submit">{submitting ? 'Cancelling...' : 'Cancel order'}</button></ModalFooter></form></ModalPanel></ModalViewport>}
    </div>
  )
}

function Input({ label, name, placeholder, type = 'text', defaultValue }: { label: string; name: string; placeholder: string; type?: string; defaultValue?: string }) {
  return (
    <label className="text-sm font-bold text-fleet-muted">
      {label}
      <input className="mt-2 min-h-11 w-full rounded-xl border border-fleet-line px-3 font-semibold outline-none focus:ring-4 focus:ring-blue-100" defaultValue={defaultValue} name={name} placeholder={placeholder} step="any" type={type} />
    </label>
  )
}

function Detail({ label, value }: { label: string; value?: string | null }) { return <div className="min-w-0 rounded-lg border border-slate-200 p-3"><dt className="text-xs font-bold text-slate-500">{label}</dt><dd className="mt-1 break-words text-sm font-bold capitalize">{value || 'Not assigned'}</dd></div> }
