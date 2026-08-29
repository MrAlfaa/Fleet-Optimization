import { Boxes, CheckCircle2, MapPinned, PackageSearch, RefreshCw, TriangleAlert } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { OpenStreetMapPanel, type OpenStreetMapMarker } from '../components/OpenStreetMapPanel'
import { Card, LoadingState, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import type { LoadConsolidation } from '../features/loadOptimization/types'
import { loadOptimizationService } from '../services/loadOptimizationService'
import { showToast } from '../utils/toast'

function localDate() {
  const today = new Date()
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
}

const REGION_COLORS = ['#2563eb', '#059669', '#d97706', '#7c3aed', '#dc2626', '#0891b2']

export function ParcelConsolidationPage() {
  const navigate = useNavigate()
  const [deliveryDate, setDeliveryDate] = useState(localDate)
  const [deliveryPeriod, setDeliveryPeriod] = useState<'first_half' | 'second_half'>('first_half')
  const [snapshot, setSnapshot] = useState<LoadConsolidation | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  const loadSnapshot = useCallback(async () => {
    setLoading(true)
    try {
      setSnapshot(await loadOptimizationService.consolidation(deliveryDate, deliveryPeriod))
    } catch (error) {
      setSnapshot(null)
      showToast({
        title: 'Unable to load parcel consolidation',
        message: error instanceof Error ? error.message : 'Unable to load the parcel batch',
        tone: 'error',
      })
    } finally {
      setLoading(false)
    }
  }, [deliveryDate, deliveryPeriod])

  useEffect(() => { queueMicrotask(() => { void loadSnapshot() }) }, [loadSnapshot])

  const markers = useMemo<OpenStreetMapMarker[]>(() => [{
    id: 'colombo-central-branch',
    label: 'H',
    title: 'Colombo Central Branch',
    subtitle: 'Fixed parcel origin',
    position: { latitude: 6.9271, longitude: 79.8612 },
    color: '#047857',
    kind: 'branch' as const,
  }, ...(snapshot?.parcel_points ?? []).map((point) => ({
    id: point.parcel_id,
    label: String(point.region_id + 1),
    title: point.order_code || point.parcel_id,
    subtitle: `Region ${point.region_id + 1}${point.zone_id ? ` · ${point.zone_id}` : ''}`,
    position: { latitude: point.latitude, longitude: point.longitude },
    color: REGION_COLORS[point.region_id % REGION_COLORS.length],
  }))], [snapshot])

  const optimizeAll = async () => {
    if (!snapshot?.parcel_count || submitting) return
    setSubmitting(true)
    try {
      const result = await loadOptimizationService.createConsolidation({
        delivery_date: deliveryDate,
        delivery_period: deliveryPeriod,
        seed: 17,
      })
      showToast({
        title: result.reused ? 'Existing consolidation opened' : 'Parcels consolidated',
        message: `${result.consolidation.consolidation_id} contains ${result.consolidation.parcel_count} parcels.`,
        tone: 'success',
      })
      navigate(`/route-planning?consolidation=${encodeURIComponent(result.consolidation.consolidation_id)}`)
    } catch (error) {
      showToast({
        title: 'Unable to consolidate parcels',
        message: error instanceof Error ? error.message : 'The parcel batch could not be locked.',
        tone: 'error',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return <div className="space-y-5">
    <PageHeader
      title="Parcel Consolidation"
      description="Review delivery regions created from Parcel Gallery records before load optimization."
      eyebrow={<StatusBadge tone="green">Live Parcel Gallery source</StatusBadge>}
      action={<>
        <SecondaryButton onClick={() => navigate('/deliveries')}><Boxes className="h-4 w-4" /> Open Parcel Gallery</SecondaryButton>
        <SecondaryButton onClick={() => void loadSnapshot()}><RefreshCw className="h-4 w-4" /> Refresh</SecondaryButton>
      </>}
    />

    <Card>
      <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_minmax(220px,0.7fr)_auto] md:items-end">
        <label className="text-sm font-semibold text-fleet-ink">Delivery date
          <input className="mt-2 w-full rounded-lg border border-fleet-line px-3 py-2.5" onChange={(event) => setDeliveryDate(event.target.value)} type="date" value={deliveryDate} />
        </label>
        <label className="text-sm font-semibold text-fleet-ink">Delivery period
          <select className="mt-2 w-full rounded-lg border border-fleet-line px-3 py-2.5" onChange={(event) => setDeliveryPeriod(event.target.value as 'first_half' | 'second_half')} value={deliveryPeriod}>
            <option value="first_half">First Half (08:00-12:00)</option>
            <option value="second_half">Second Half (13:00-17:00)</option>
          </select>
        </label>
        <PrimaryButton disabled={!snapshot?.parcel_count || submitting} onClick={() => void optimizeAll()}><PackageSearch className="h-4 w-4" /> {submitting ? 'Consolidating...' : 'Optimize all regions'}</PrimaryButton>
      </div>
    </Card>

    {loading ? <LoadingState label="Loading parcel consolidation..." /> : <>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          { label: 'Eligible parcels', value: snapshot?.parcel_count ?? 0, icon: Boxes },
          { label: 'Delivery regions', value: snapshot?.regions.length ?? 0, icon: MapPinned },
          { label: 'Needs parcel correction', value: snapshot?.exception_count ?? 0, icon: TriangleAlert },
          { label: 'Excluded from batch', value: snapshot?.excluded_count ?? 0, icon: PackageSearch },
        ].map(({ label, value, icon: Icon }) => <div className="rounded-lg border border-fleet-line bg-white p-4 shadow-card" key={label}>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase text-fleet-muted"><Icon className="h-4 w-4 text-blue-600" />{label}</div>
          <div className="mt-2 text-2xl font-bold">{value}</div>
        </div>)}
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(340px,0.65fr)]">
        <Card title="Cluster snapshot">
          {markers.length > 1 ? <OpenStreetMapPanel
            circles={(snapshot?.regions ?? []).map((region) => ({ id: `region-${region.region_id}`, center: region.centroid, radiusMeters: Math.max(450, Math.min(1800, region.parcel_count * 90)), color: REGION_COLORS[region.region_id % REGION_COLORS.length], fillOpacity: 0.1, title: `Region ${region.region_id + 1}`, subtitle: `${region.parcel_count} parcels` }))}
            className="min-h-[420px]"
            markers={markers}
          /> : <div className="grid min-h-[300px] place-items-center text-sm text-fleet-muted">No eligible parcel coordinates for this batch.</div>}
          <div className="mt-3 flex flex-wrap gap-3 text-xs font-semibold text-fleet-muted"><span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-emerald-700" />Branch origin</span>{(snapshot?.regions ?? []).map((region) => <span className="inline-flex items-center gap-1.5" key={region.region_id}><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: REGION_COLORS[region.region_id % REGION_COLORS.length] }} />Region {region.region_id + 1}</span>)}</div>
        </Card>
        <Card title="Consolidated regions">
          <div className="space-y-3">
            {(snapshot?.regions ?? []).map((region) => <div className="rounded-lg border border-fleet-line p-4" key={region.region_id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-bold">Region {region.region_id + 1}</div>
                  <div className="mt-1 text-sm text-fleet-muted">{region.parcel_count} parcels</div>
                </div>
                <StatusBadge tone="blue"><CheckCircle2 className="mr-1 h-3.5 w-3.5" />Included</StatusBadge>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs font-semibold text-fleet-muted"><span>{region.total_weight_kg?.toFixed(1) ?? '0'} kg</span><span>{region.total_volume_m3?.toFixed(3) ?? '0'} m³</span></div>
            </div>)}
            {!snapshot?.regions.length && <div className="rounded-lg bg-slate-50 p-5 text-sm text-fleet-muted">Add valid parcels to Parcel Gallery for this date and period.</div>}
          </div>
        </Card>
      </div>
    </>}
  </div>
}
