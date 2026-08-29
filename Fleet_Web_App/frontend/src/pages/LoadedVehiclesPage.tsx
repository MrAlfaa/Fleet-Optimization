import { Box, MapPinned, RefreshCw, Truck } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, ErrorState, LoadingState, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import type { LoadPlan, VehicleSuggestion, VirtualLoad } from '../features/loadOptimization/types'
import { saveRouteDeliverySelection, saveRoutePlanningContext } from '../features/deliveries/routeSelection'
import { loadOptimizationService } from '../services/loadOptimizationService'

export function LoadedVehiclesPage() {
  const navigate = useNavigate()
  const [plans, setPlans] = useState<LoadPlan[]>([])
  const [plan, setPlan] = useState<LoadPlan | null>(null)
  const [suggestions, setSuggestions] = useState<VehicleSuggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [busyLoadId, setBusyLoadId] = useState('')

  const loadWorkspace = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await loadOptimizationService.listPlans({ status: 'approved' })
      setPlans(response.items)
      const nextPlan = response.items[0] ?? null
      setPlan(nextPlan)
      setSuggestions(nextPlan ? (await loadOptimizationService.suggestions(nextPlan.plan_id)).suggestions : [])
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load assigned vehicles')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    queueMicrotask(() => { void loadWorkspace() })
  }, [])

  const selectPlan = async (planId: string) => {
    const selected = plans.find((item) => item.plan_id === planId) ?? null
    setPlan(selected)
    setSuggestions(selected ? (await loadOptimizationService.suggestions(selected.plan_id)).suggestions : [])
  }

  const assign = async (load: VirtualLoad, vehicleId: string) => {
    if (!plan || !vehicleId) return
    setBusyLoadId(load.load_id)
    setError('')
    try {
      const updated = await loadOptimizationService.assign(plan.plan_id, load.load_id, vehicleId)
      setPlan(updated)
      setPlans((items) => items.map((item) => item.plan_id === updated.plan_id ? updated : item))
      setSuggestions((await loadOptimizationService.suggestions(updated.plan_id)).suggestions)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to confirm the physical vehicle')
    } finally {
      setBusyLoadId('')
    }
  }

  const routeLoad = (load: VirtualLoad) => {
    if (!plan || !load.assigned_vehicle_id) return
    saveRouteDeliverySelection(load.parcel_ids)
    saveRoutePlanningContext({ vehicleId: load.assigned_vehicle_id, planId: plan.plan_id, loadId: load.load_id })
    navigate('/route-planning')
  }

  const loads = useMemo(() => plan?.selected_option?.loads ?? [], [plan])
  if (loading) return <LoadingState label="Loading fleet handoff" />
  if (error && !plans.length) return <ErrorState message={error} onRetry={loadWorkspace} />

  return <div className="space-y-5">
    <PageHeader title="Loaded Vehicles" description="Confirm a compatible physical vehicle for every approved virtual load before route planning." action={<SecondaryButton onClick={() => void loadWorkspace()}><RefreshCw className="h-4 w-4" /> Refresh</SecondaryButton>} />
    {error && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>}
    <Card title="Fleet handoff filters"><label className="text-sm font-semibold">Approved plan<select className="mt-2 w-full rounded-lg border border-fleet-line px-3 py-2.5" onChange={(event) => void selectPlan(event.target.value)} value={plan?.plan_id ?? ''}><option value="">Select approved plan</option>{plans.map((item) => <option key={item.plan_id} value={item.plan_id}>{item.delivery_date} · {item.delivery_period.replace('_', ' ')} · revision {item.revision}</option>)}</select></label></Card>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><FleetMetric label="Vehicles shown" value={String(loads.length)} /><FleetMetric label="Ready for routing" value={String(loads.filter((load) => load.assigned_vehicle_id).length)} /><FleetMetric label="Parcels" value={String(loads.reduce((sum, load) => sum + load.parcel_count, 0))} /><FleetMetric label="Unassigned" value={String(loads.filter((load) => !load.assigned_vehicle_id).length)} /></div>
    <div className="grid gap-4 lg:grid-cols-2">
      {loads.map((load) => {
        const matches = suggestions.find((item) => item.load_id === load.load_id)?.matches ?? []
        return <Card key={load.load_id} title={load.load_id} action={<StatusBadge tone={load.assigned_vehicle_id ? 'green' : 'amber'}>{load.assigned_vehicle_id ? 'Vehicle confirmed' : 'Awaiting assignment'}</StatusBadge>}>
          <div className="grid grid-cols-2 gap-4 text-sm"><LoadFact label="Vehicle type" value={load.vehicle_type_code.replaceAll('_', ' ')} /><LoadFact label="Parcels" value={String(load.parcel_count)} /><LoadFact label="Weight" value={`${load.used_weight_kg.toFixed(1)} kg`} /><LoadFact label="Volume" value={`${load.used_volume_m3.toFixed(2)} m³`} /></div>
          <div className="mt-5 flex flex-wrap gap-2">
            <SecondaryButton onClick={() => navigate(`/load-plans/${plan?.plan_id}?load=${encodeURIComponent(load.load_id)}`)}><Box className="h-4 w-4" /> View 3D load</SecondaryButton>
            {!load.assigned_vehicle_id && <label className="min-w-[220px] flex-1 text-sm font-semibold"><span className="sr-only">Vehicle for {load.load_id}</span><select aria-label={`Vehicle for ${load.load_id}`} className="min-h-10 w-full rounded-lg border border-fleet-line px-3" disabled={busyLoadId === load.load_id} onChange={(event) => void assign(load, event.target.value)} value=""><option value="">Select compatible vehicle</option>{matches.map((match) => <option key={match.vehicle.id} value={match.vehicle.id}>{match.vehicle.registration_number}</option>)}</select></label>}
            {load.assigned_vehicle_id && <PrimaryButton onClick={() => routeLoad(load)}><MapPinned className="h-4 w-4" /> Continue to route planning</PrimaryButton>}
          </div>
        </Card>
      })}
      {!loads.length && <Card className="lg:col-span-2"><div className="grid min-h-[240px] place-items-center text-center"><div><Truck className="mx-auto h-9 w-9 text-slate-400" /><p className="mt-3 text-sm text-fleet-muted">Approve a load plan before fleet handoff.</p></div></div></Card>}
    </div>
  </div>
}

function FleetMetric({ label, value }: { label: string; value: string }) { return <div className="rounded-lg border border-fleet-line bg-white p-4 shadow-card"><div className="text-xs font-bold uppercase text-fleet-muted">{label}</div><div className="mt-2 text-2xl font-black">{value}</div></div> }
function LoadFact({ label, value }: { label: string; value: string }) { return <div><div className="text-xs font-bold uppercase text-fleet-muted">{label}</div><div className="mt-1 font-bold capitalize">{value}</div></div> }
