import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, House, MapPinned, Play, RefreshCcw, Route, ShieldCheck, Truck } from 'lucide-react'
import { OpenStreetMapPanel } from '../../components/OpenStreetMapPanel'
import { Card, DataTable, ErrorState, LoadingState, PrimaryButton, SecondaryButton, StatusBadge } from '../../components/UI'
import type { LoadPlan, VehicleSuggestion } from '../loadOptimization/types'
import type { OperationalBranch, RoutePlan, RouteSet } from '../../types'
import { authService } from '../../services/authService'
import { driverAdminService, type ManagedDriver } from '../../services/driverAdminService'
import { loadOptimizationService } from '../../services/loadOptimizationService'
import { operationsService } from '../../services/operationsService'
import { canAccess } from '../../utils/permissions'
import { routeSetWorkflow } from './routeSetWorkflow'

export function RouteSetDispatchWorkspace({ planId }: { planId: string }) {
  const user = authService.getSession()
  const [plan, setPlan] = useState<LoadPlan | null>(null)
  const [suggestions, setSuggestions] = useState<VehicleSuggestion[]>([])
  const [routeSet, setRouteSet] = useState<RouteSet | null>(null)
  const [drivers, setDrivers] = useState<ManagedDriver[]>([])
  const [branch, setBranch] = useState<OperationalBranch | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const hydrate = async () => {
    setLoading(true)
    setError('')
    try {
      const [nextPlan, nextSuggestions, nextDrivers, nextBranch] = await Promise.all([
        loadOptimizationService.getPlan(planId),
        loadOptimizationService.suggestions(planId),
        driverAdminService.listAssignable(),
        operationsService.getOperationalBranch(),
      ])
      setPlan(nextPlan)
      setSuggestions(nextSuggestions.suggestions)
      setDrivers(nextDrivers)
      setBranch(nextBranch)
      if (nextPlan.route_set_id) {
        const existingSet = await operationsService.getRouteSet(nextPlan.route_set_id)
        setRouteSet(existingSet)
        setSelectedRouteId((current) => current || existingSet.routes[0]?.id || '')
      } else {
        setRouteSet(null)
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load the approved planning handoff')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    queueMicrotask(() => { void hydrate() })
    // The approved plan ID is the stable handoff key.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId])

  const assignVehicle = async (loadId: string, vehicleId: string) => {
    if (!vehicleId) return
    setBusy(true)
    setError('')
    try {
      const updated = await loadOptimizationService.assign(planId, loadId, vehicleId)
      setPlan(updated)
      setSuggestions((await loadOptimizationService.suggestions(planId)).suggestions)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to confirm this physical vehicle')
    } finally {
      setBusy(false)
    }
  }

  const generateRoutes = async () => {
    setBusy(true)
    setError('')
    try {
      const created = await operationsService.createRouteSet(planId)
      const hydrated = await operationsService.getRouteSet(created.routeSetId)
      setRouteSet(hydrated)
      setSelectedRouteId(hydrated.routes[0]?.id ?? '')
      setPlan(await loadOptimizationService.getPlan(planId))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to generate the route set')
    } finally {
      setBusy(false)
    }
  }

  const approveRoutes = async () => {
    if (!routeSet) return
    setBusy(true)
    setError('')
    try {
      const approved = await operationsService.approveRouteSet(routeSet.routeSetId)
      setRouteSet(await operationsService.getRouteSet(approved.routeSetId))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to approve this route set')
    } finally {
      setBusy(false)
    }
  }

  const assignDriver = async (routeId: string, driverId: string) => {
    if (!routeSet || !driverId) return
    setBusy(true)
    setError('')
    try {
      await operationsService.assignRouteDriver(routeSet.routeSetId, routeId, driverId)
      setRouteSet(await operationsService.getRouteSet(routeSet.routeSetId))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to assign this driver')
    } finally {
      setBusy(false)
    }
  }

  const dispatch = async () => {
    if (!routeSet) return
    setBusy(true)
    setError('')
    try {
      const dispatched = await operationsService.dispatchRouteSet(routeSet.routeSetId)
      setRouteSet(await operationsService.getRouteSet(dispatched.routeSetId))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to dispatch all approved routes')
    } finally {
      setBusy(false)
    }
  }

  const selectedRoute = routeSet?.routes.find((route) => route.id === selectedRouteId) ?? routeSet?.routes[0] ?? null
  const workflow = routeSetWorkflow(plan, routeSet)
  const markers = useMemo(() => routeMarkers(branch, selectedRoute), [branch, selectedRoute])
  const canAssignVehicle = canAccess(user, 'load_optimization.assign')
  const canGenerateRoutes = canAccess(user, 'routes.optimize')
  const canApproveRoutes = canAccess(user, 'routes.approve')
  const canDispatch = canAccess(user, 'routes.dispatch')

  if (loading) return <LoadingState label="Loading route and dispatch workflow" />
  if (!plan || !branch) return <ErrorState message={error || 'The approved load plan is unavailable'} onRetry={hydrate} />
  if (plan.status !== 'approved') return <ErrorState message="Approve one load candidate before opening Route and Dispatch." onRetry={hydrate} />

  return <div>
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3"><div><StatusBadge tone={routeSet?.status === 'dispatched' ? 'green' : routeSet?.status === 'approved' ? 'blue' : 'amber'}>{routeSet?.status?.replaceAll('_', ' ') ?? 'Vehicle confirmation'}</StatusBadge><h1 className="mt-2 text-2xl font-black text-fleet-ink">Route and dispatch control</h1><p className="mt-1 text-sm font-semibold text-fleet-muted">{plan.consolidation_id || plan.plan_id} - {plan.delivery_date} - {plan.delivery_period === 'first_half' ? 'First Half' : 'Second Half'}</p></div><SecondaryButton onClick={() => void hydrate()}><RefreshCcw className="h-4 w-4" /> Refresh</SecondaryButton></div>
    {error && <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>}

    <div className="mb-5 grid gap-3 md:grid-cols-4"><Stage active={!workflow.allVehiclesAssigned} complete={workflow.allVehiclesAssigned} icon={Truck} label="1. Confirm vehicles" /><Stage active={workflow.allVehiclesAssigned && !routeSet} complete={Boolean(routeSet)} icon={Route} label="2. Generate routes" /><Stage active={routeSet?.status === 'review_required'} complete={['approved', 'dispatching', 'dispatched'].includes(routeSet?.status ?? '')} icon={ShieldCheck} label="3. Approve routes" /><Stage active={routeSet?.status === 'approved'} complete={routeSet?.status === 'dispatched'} icon={Play} label="4. Assign and dispatch" /></div>

      <Card className="mb-5" title="Physical vehicle confirmation">
      <DataTable headers={['Virtual load', 'Required type', 'Parcels', 'Capacity use', 'Compatible physical vehicle', 'Readiness']}>
        {(plan.selected_option?.loads ?? []).map((load) => {
          const matches = suggestions.find((item) => item.load_id === load.load_id)?.matches ?? []
          return <tr key={load.load_id}><td className="px-5 py-4 font-black text-fleet-blue">{load.load_id}</td><td className="px-5 py-4 font-semibold">{load.vehicle_type_code.replaceAll('_', ' ')}</td><td className="px-5 py-4">{load.parcel_count}</td><td className="px-5 py-4">{Math.round((load.used_volume_m3 / Math.max(load.capacity_m3, 0.01)) * 100)}%</td><td className="px-5 py-4">{load.assigned_vehicle_id ? <span className="font-bold">{matches.find((match) => match.vehicle.id === load.assigned_vehicle_id)?.vehicle.registration_number ?? load.assigned_vehicle_id}</span> : canAssignVehicle ? <select aria-label={`Vehicle for ${load.load_id}`} className="min-h-10 min-w-48 rounded-lg border border-fleet-line px-3" disabled={busy || Boolean(routeSet)} onChange={(event) => void assignVehicle(load.load_id, event.target.value)} value=""><option value="">Select compatible vehicle</option>{matches.map((match) => <option key={match.vehicle.id} value={match.vehicle.id}>{match.vehicle.registration_number}</option>)}</select> : <span>Permission required</span>}</td><td className="px-5 py-4">{load.assigned_vehicle_id ? <StatusBadge tone="green">Confirmed</StatusBadge> : matches.length ? <StatusBadge tone="blue">{matches.length} available</StatusBadge> : <StatusBadge tone="amber">No compatible vehicle</StatusBadge>}</td></tr>
        })}
      </DataTable>
      <div className="mt-4 flex flex-wrap items-center justify-between gap-3"><p className="text-sm font-semibold text-fleet-muted">Routes can be generated only after every approved virtual load has a compatible, dispatch-ready registration.</p>{canGenerateRoutes && <PrimaryButton disabled={busy || !workflow.canGenerateRoutes} onClick={generateRoutes}><MapPinned className="h-4 w-4" /> Generate route set</PrimaryButton>}</div>
    </Card>

    {routeSet && <><div className="mb-5 grid gap-5 xl:grid-cols-[minmax(280px,0.7fr)_minmax(0,1.5fr)]"><Card title="Route set review"><div className="space-y-2">{routeSet.routes.map((route, index) => <button className={`w-full rounded-lg border p-3 text-left ${selectedRoute?.id === route.id ? 'border-blue-400 bg-blue-50' : 'border-fleet-line hover:bg-slate-50'}`} key={route.id} onClick={() => setSelectedRouteId(route.id)} type="button"><div className="flex items-center justify-between gap-2"><span className="font-black">Route {index + 1}</span><StatusBadge tone={route.status === 'approved' || route.status === 'dispatched' ? 'green' : 'blue'}>{route.status ?? 'optimized'}</StatusBadge></div><div className="mt-1 text-xs font-semibold text-fleet-muted">{route.routeCode || route.id} - {deliveryStopCount(route)} delivery stops - {route.eta}</div></button>)}</div>{workflow.canApproveRoutes && canApproveRoutes && <div className="mt-4 [&>button]:w-full [&>button]:justify-center"><PrimaryButton disabled={busy} onClick={approveRoutes}><CheckCircle2 className="h-4 w-4" /> Approve all routes</PrimaryButton></div>}</Card><Card title={`Selected route path - ${deliveryStopCount(selectedRoute)} delivery stops`}><OpenStreetMapPanel className="min-h-[380px]" markers={markers} polylines={selectedRoute && selectedRoute.mapPath.length > 1 ? [{ id: selectedRoute.id, path: selectedRoute.mapPath, color: '#1d4ed8' }] : []} /></Card></div>

      <Card title="Driver assignment and dispatch"><DataTable headers={['Route', 'Vehicle', 'Stops', 'Driver', 'Status']}>{routeSet.routes.map((route) => {
        const assignedElsewhere = new Set(routeSet.routes.filter((item) => item.id !== route.id && item.driver && item.driver !== 'Unassigned').map((item) => item.driver))
        const availableDrivers = drivers.filter((driver) => !assignedElsewhere.has(driver.id))
        return <tr key={route.id}><td className="px-5 py-4 font-black text-fleet-blue">{route.routeCode || route.id}</td><td className="px-5 py-4">{vehicleRegistration(suggestions, route.vehicle)}</td><td className="px-5 py-4">{deliveryStopCount(route)}</td><td className="px-5 py-4">{route.driver && route.driver !== 'Unassigned' ? <span className="font-bold">{drivers.find((driver) => driver.id === route.driver)?.full_name ?? route.driver}</span> : workflow.canAssignDrivers && canDispatch ? availableDrivers.length ? <select aria-label={`Driver for ${route.routeCode || route.id}`} className="min-h-10 min-w-48 rounded-lg border border-fleet-line px-3" disabled={busy} onChange={(event) => void assignDriver(route.id, event.target.value)} value=""><option value="">Select enrolled driver</option>{availableDrivers.map((driver) => <option key={driver.id} value={driver.id}>{driver.full_name} (@{driver.username})</option>)}</select> : <StatusBadge tone="amber">No unassigned driver</StatusBadge> : <span className="text-fleet-muted">Available after route approval</span>}</td><td className="px-5 py-4"><StatusBadge tone={route.status === 'dispatched' ? 'green' : route.driver !== 'Unassigned' ? 'blue' : 'slate'}>{route.status === 'dispatched' ? 'Sent to driver' : route.driver !== 'Unassigned' ? 'Driver confirmed' : 'Pending'}</StatusBadge></td></tr>
      })}</DataTable><div className="mt-4 flex flex-wrap items-center justify-between gap-3"><p className="text-sm font-semibold text-fleet-muted">Dispatch publishes only approved routes with unique enrolled drivers and confirmed vehicles to the mobile app.</p>{canDispatch && <PrimaryButton disabled={busy || !workflow.canDispatch} onClick={dispatch}><Play className="h-4 w-4" /> Dispatch all routes</PrimaryButton>}</div></Card>
    </>}
  </div>
}

function routeMarkers(branch: OperationalBranch | null, route: RoutePlan | null) {
  if (!branch) return []
  return [{ id: branch.id, kind: 'branch' as const, label: 'H', title: branch.name, subtitle: 'Fixed origin and return point', position: { latitude: branch.latitude, longitude: branch.longitude }, color: '#047857' }, ...(route?.stops ?? []).filter((stop) => stop.status !== 'Origin' && stop.status !== 'Return' && stop.latitude !== null && stop.longitude !== null).map((stop) => ({ id: `${route?.id}-${stop.sequence}`, label: String(stop.sequence), title: stop.name, subtitle: stop.eta, position: { latitude: stop.latitude as number, longitude: stop.longitude as number }, color: '#f59e0b' }))]
}

function deliveryStopCount(route: RoutePlan | null) {
  return route?.stops.filter((stop) => stop.status !== 'Origin' && stop.status !== 'Return').length ?? 0
}

function vehicleRegistration(suggestions: VehicleSuggestion[], vehicleId: string) {
  return suggestions.flatMap((item) => item.matches).find((match) => match.vehicle.id === vehicleId)?.vehicle.registration_number ?? vehicleId
}

function Stage({ icon: Icon, label, active, complete }: { icon: typeof House; label: string; active: boolean; complete: boolean }) {
  const classes = complete ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : active ? 'border-blue-300 bg-blue-50 text-blue-800' : 'border-fleet-line bg-white text-fleet-muted'
  return <div className={`flex min-h-16 items-center gap-3 rounded-lg border px-4 ${classes}`}><span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white/80"><Icon className="h-4 w-4" /></span><span className="text-sm font-black">{label}</span></div>
}
