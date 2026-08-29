import { useEffect, useState } from 'react'
import { Activity, AlertTriangle, ArrowRight, MapPin, Route, ShieldCheck, Truck, Wrench } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Line, LineChart } from 'recharts'
import { OpenStreetMapPanel } from '../components/OpenStreetMapPanel'
import { Card, ErrorState, LoadingState, MetricCard, PageHeader, StatusBadge } from '../components/UI'
import { formatNumber } from '../utils/format'
import { buildLiveMapView } from '../utils/liveMap'
import { useAsyncData } from '../hooks/useAsyncData'
import { fleetService } from '../services/fleetService'
import { forecastService } from '../services/forecastService'
import { operationsService } from '../services/operationsService'
import { intelligenceService } from '../services/intelligenceService'

async function loadLiveNetwork() {
  const trips = await operationsService.listLiveTrips()
  const selectedTrip = trips.find((trip) => trip.tripStatus === 'active') ?? trips[0]
  const locations = selectedTrip
    ? await operationsService.getLiveTripLocations(selectedTrip.routeId)
    : []
  return { trips, locations, updatedAt: new Date().toISOString() }
}

export function DashboardPage() {
  const navigate = useNavigate()
  const [liveState, setLiveState] = useState<'live' | 'stale'>('live')
  const { data, error, loading, reload, setData } = useAsyncData(async () => {
    const [summary, health, demandForecasts, routeTrend, alerts, liveNetwork, readiness] = await Promise.all([
      fleetService.getDashboardSummary(),
      fleetService.getHealthDistribution(),
      forecastService.listForecasts({ limit: 4 }),
      operationsService.getRouteTrend(),
      fleetService.getRecentAlerts(3),
      loadLiveNetwork(),
      intelligenceService.getFleetReadiness(),
    ])
    return { summary, health, demandForecasts, routeTrend, alerts, liveNetwork, readiness }
  }, [])

  useEffect(() => {
    let cancelled = false
    const timer = window.setInterval(async () => {
      try {
        const liveNetwork = await loadLiveNetwork()
        if (cancelled) return
        setData((current) => current ? { ...current, liveNetwork } : current)
        setLiveState('live')
      } catch {
        if (!cancelled) setLiveState('stale')
      }
    }, 15000)

    return () => {
      cancelled = true
      window.clearInterval(timer)
    }
  }, [setData])

  if (loading) return <LoadingState />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load dashboard data'} onRetry={reload} />

  const activeVehicles = Number(data.summary.active_vehicles ?? 0)
  const underMaintenance = Number(data.summary.under_maintenance ?? 0)
  const criticalVehicles = Number(data.summary.critical_vehicles ?? 0)
  const routeSummary = (data.summary.route_optimization ?? {}) as Record<string, unknown>
  const activeRoutes = Number(routeSummary.active_routes_count ?? routeSummary.dispatched_routes_count ?? 0)
  const healthyCount = Number(data.health.healthy ?? 0)
  const warningCount = Number(data.health.warning ?? 0)
  const unknownCount = Number(data.health.unknown ?? 0)
  const criticalCount = Number(data.health.critical ?? 0)
  const totalHealth = healthyCount + warningCount + unknownCount + criticalCount || 1
  const riskProfile = [
    { name: 'Optimal', value: Math.round((healthyCount / totalHealth) * 100), color: '#1d4ed8' },
    { name: 'Watch', value: Math.round(((warningCount + unknownCount) / totalHealth) * 100), color: '#64748b' },
    { name: 'Critical', value: Math.round((criticalCount / totalHealth) * 100), color: '#dc2626' },
  ]
  const healthScore = Math.max(0, 100 - riskProfile[2].value - Math.round(riskProfile[1].value / 2))
  const liveMap = buildLiveMapView(data.liveNetwork.trips, data.liveNetwork.locations)
  const selectedLocation = liveMap.selectedTrip?.latestLocation
  const mapCenter = selectedLocation
    ? { latitude: selectedLocation.latitude, longitude: selectedLocation.longitude }
    : undefined
  const lastUpdate = selectedLocation?.recordedAt ?? data.liveNetwork.updatedAt
  const formattedLastUpdate = Number.isNaN(Date.parse(lastUpdate))
    ? lastUpdate
    : new Date(lastUpdate).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  return (
    <div>
      <PageHeader
        title="Dashboard Overview"
        description="Executive view of fleet health, demand load, dispatch activity, and active operational risk."
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={Truck} label="Active Vehicles" tone="blue" trend="Available now" value={formatNumber(activeVehicles)} />
        <MetricCard icon={Wrench} label="Under Maintenance" tone="amber" trend="Scheduled" value={formatNumber(underMaintenance)} />
        <MetricCard icon={AlertTriangle} label="Critical Risk" tone="red" trend="Needs action" value={formatNumber(criticalVehicles)} />
        <MetricCard icon={Route} label="Active Routes" tone="green" trend="In operation" value={formatNumber(activeRoutes)} />
      </div>

      <Card
        action={<button className="inline-flex items-center gap-1 text-xs font-bold text-fleet-blue" onClick={() => navigate('/fleet-readiness')} type="button">View readiness <ArrowRight className="h-3.5 w-3.5" /></button>}
        className="mt-5"
        title="Fleet Readiness"
      >
        <div className="grid gap-4 md:grid-cols-4">
          <div><div className="text-xs font-semibold text-fleet-muted">Vehicles required</div><div className="mt-1 text-2xl font-bold">{data.readiness.requiredVehicles}</div></div>
          <div><div className="text-xs font-semibold text-fleet-muted">Safe for dispatch</div><div className="mt-1 text-2xl font-bold text-emerald-700">{data.readiness.eligibleVehicles}</div></div>
          <div><div className="text-xs font-semibold text-fleet-muted">Capacity gap</div><div className="mt-1 text-2xl font-bold text-amber-700">{data.readiness.capacityGap}</div></div>
          <div><div className="text-xs font-semibold text-fleet-muted">Blocked critical</div><div className="mt-1 text-2xl font-bold text-red-700">{data.readiness.blockedVehicles}</div></div>
        </div>
        <div className="mt-4 flex items-start gap-2 border-t border-fleet-line pt-4">
          <ShieldCheck className="mt-0.5 h-4 w-4 text-fleet-blue" />
          <div className="space-y-1 text-sm text-fleet-muted">{data.readiness.recommendations.slice(0, 3).map((item, index) => <p key={`${item.type}-${index}`}>{item.message}</p>)}{data.readiness.recommendations.length === 0 && <p>No operational conflict detected for the latest forecast date.</p>}</div>
        </div>
      </Card>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.65fr_0.85fr]">
        <Card
          action={<button className="focus-ring rounded-md px-2 py-1 text-xs font-bold text-fleet-blue hover:bg-blue-50" onClick={() => navigate('/live-trips')} type="button">Expand Map</button>}
          title="Live Network Activity"
        >
          <OpenStreetMapPanel
            center={mapCenter}
            className="min-h-[340px]"
            markers={liveMap.markers}
            polylines={liveMap.trail.length > 1 ? [{ id: 'dashboard-live-trail', path: liveMap.trail, color: '#16A34A' }] : []}
          >
            <div className="absolute left-4 top-4 max-w-[calc(100%-2rem)] rounded-lg bg-white/95 p-4 shadow-soft ring-1 ring-fleet-line backdrop-blur-sm">
              <div className="flex items-center gap-2">
                <span className={`relative flex h-2.5 w-2.5 ${liveState === 'live' ? '' : 'opacity-70'}`}>
                  {liveState === 'live' && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60 motion-reduce:animate-none" />}
                  <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${liveState === 'live' ? 'bg-emerald-600' : 'bg-amber-500'}`} />
                </span>
                <span className="text-xs font-bold uppercase text-fleet-ink">{liveState === 'live' ? 'Live feed' : 'Last known data'}</span>
                <span className="text-xs font-medium text-fleet-muted">Updated {formattedLastUpdate}</span>
              </div>
              <div className="mt-3 flex items-end gap-5">
                <div>
                  <div className="text-2xl font-bold text-fleet-ink">{formatNumber(data.liveNetwork.trips.length)}</div>
                  <div className="text-xs font-medium text-fleet-muted">active routes</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-fleet-ink">{liveMap.progress.completedStops}/{liveMap.progress.totalStops}</div>
                  <div className="text-xs font-medium text-fleet-muted">stops completed</div>
                </div>
              </div>
            </div>

            {data.liveNetwork.trips.length === 0 ? (
              <div className="absolute inset-x-4 bottom-4 rounded-lg bg-white/95 p-4 shadow-soft ring-1 ring-fleet-line backdrop-blur-sm">
                <div className="flex items-start gap-3">
                  <Activity className="mt-0.5 h-5 w-5 text-fleet-blue" />
                  <div>
                    <div className="text-sm font-bold text-fleet-ink">No active driver trips</div>
                    <p className="mt-1 text-xs font-medium text-fleet-muted">Dispatch a route and start the trip from the driver app to publish live GPS activity.</p>
                  </div>
                </div>
              </div>
            ) : liveMap.markers.length === 0 ? (
              <div className="absolute inset-x-4 bottom-4 rounded-lg bg-white/95 p-4 shadow-soft ring-1 ring-fleet-line backdrop-blur-sm">
                <div className="flex items-start gap-3">
                  <MapPin className="mt-0.5 h-5 w-5 text-amber-600" />
                  <div>
                    <div className="text-sm font-bold text-fleet-ink">Waiting for driver GPS</div>
                    <p className="mt-1 text-xs font-medium text-fleet-muted">The trip is active, but no valid location has been received yet.</p>
                  </div>
                </div>
              </div>
            ) : null}
          </OpenStreetMapPanel>
        </Card>

        <Card title="Fleet Risk Profile">
          <div className="relative">
            <ResponsiveContainer height={210} width="100%">
              <PieChart>
                <Pie data={riskProfile} dataKey="value" innerRadius={58} outerRadius={82} paddingAngle={4}>
                  {riskProfile.map((item) => (
                    <Cell fill={item.color} key={item.name} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
              <div className="text-3xl font-bold">{healthScore}</div>
              <div className="text-xs font-medium text-fleet-muted">Health Score</div>
            </div>
          </div>
          <div className="space-y-2">
            {riskProfile.map((item) => (
              <div className="flex items-center justify-between text-sm font-medium" key={item.name}>
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: item.color }} />
                  {item.name}
                </span>
                <span>{item.value}%</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="mt-5 grid items-stretch gap-5 xl:grid-cols-3">
        <Card className="h-full xl:col-span-1" title="Route Efficiency">
          <ResponsiveContainer height={230} width="100%">
            <LineChart data={data.routeTrend} margin={{ top: 12, right: 12, bottom: 0, left: -14 }}>
              <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" />
              <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 12, fontWeight: 500 }} tickLine={false} />
              <YAxis allowDecimals={false} tick={{ fill: '#64748b', fontSize: 12, fontWeight: 500 }} tickLine={false} />
              <Tooltip />
              <Line dataKey="actual" stroke="#1d4ed8" strokeWidth={3} />
              <Line dataKey="planned" stroke="#94a3b8" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
        <Card className="h-full" title="Demand Forecast by Zone">
          <div className="space-y-3">
            {data.demandForecasts.map((forecast, index) => (
              <div className="flex min-w-0 items-center justify-between gap-3 rounded-lg bg-slate-50 p-3" key={`${forecast.zone}-${index}`}>
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold" title={forecast.zone}>{forecast.zone}</div>
                  <div className="text-xs font-normal text-fleet-muted">{formatNumber(forecast.predictedVolume)} predicted</div>
                </div>
                <StatusBadge tone={forecast.variance > 20 ? 'red' : forecast.variance > 10 ? 'amber' : 'green'}>
                  {forecast.variance > 0 ? '+' : ''}{forecast.variance}%
                </StatusBadge>
              </div>
            ))}
          </div>
        </Card>
        <Card className="h-full" action={<StatusBadge tone="red">{data.alerts.length} New</StatusBadge>} title="Active Alerts">
          <div className="space-y-3">
            {data.alerts.slice(0, 3).map((alert) => (
              <div className="min-w-0 rounded-lg border border-fleet-line bg-white p-3 shadow-sm" key={alert.id}>
                <div className="break-words text-sm font-semibold leading-5">{alert.title}</div>
                <p className="mt-1 break-words text-xs font-normal leading-5 text-fleet-muted">{alert.description}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
