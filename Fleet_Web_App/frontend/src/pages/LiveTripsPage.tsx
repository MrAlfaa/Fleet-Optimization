import { useEffect } from 'react'
import { Filter, Plus, RadioTower } from 'lucide-react'
import { GoogleMapPanel } from '../components/GoogleMapPanel'
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { useAsyncData } from '../hooks/useAsyncData'
import { operationsService } from '../services/operationsService'

export function LiveTripsPage() {
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [trips, summary] = await Promise.all([
      operationsService.listLiveTrips(),
      operationsService.getRouteDashboardSummary(),
    ])
    const latestTrip = trips[0]
    const [events, locations] = latestTrip
      ? await Promise.all([
        operationsService.getLiveTripEvents(latestTrip.routeId),
        operationsService.getLiveTripLocations(latestTrip.routeId),
      ])
      : [[], []]
    return { trips, events, locations, summary }
  }, [])

  useEffect(() => {
    const timer = window.setInterval(() => {
      void reload()
    }, 15000)
    return () => window.clearInterval(timer)
  }, [reload])

  if (loading) return <LoadingState />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load live route activity'} onRetry={reload} />

  const activeCount = data.trips.length
  const latestTrip = data.trips[0]
  const mapMarkers = data.trips
    .filter((trip) => trip.latestLocation)
    .map((trip) => ({
      id: trip.routeId,
      label: 'D',
      title: `${trip.routeCode} - ${trip.driverName}`,
      subtitle: `${trip.vehicleCode} | ${trip.latestLocation?.recordedAt ?? 'Waiting for GPS'}`,
      position: {
        latitude: trip.latestLocation?.latitude ?? 0,
        longitude: trip.latestLocation?.longitude ?? 0,
      },
      color: trip.tripStatus === 'active' ? '#16A34A' : '#1D4ED8',
    }))
  const trailPath = data.locations
    .slice()
    .reverse()
    .map((location) => ({ latitude: location.latitude, longitude: location.longitude }))

  return (
    <div>
      <PageHeader
        action={<div className="flex gap-3"><SecondaryButton><Filter className="h-4 w-4" /> Filter</SecondaryButton><PrimaryButton><Plus className="h-4 w-4" /> New Dispatch</PrimaryButton></div>}
        description={`Monitoring ${activeCount} active trips. Auto-refreshes every 15 seconds.`}
        title="Active Deployments"
      />
      <div className="grid gap-5 xl:grid-cols-[1fr_430px]">
        <Card action={<div className="flex gap-2"><StatusBadge tone="green">{activeCount} Live</StatusBadge><StatusBadge tone="amber">{Number(data.summary.pending_deliveries ?? 0)} Pending</StatusBadge></div>} title="Live Fleet Map">
          <GoogleMapPanel
            className="min-h-[760px]"
            markers={mapMarkers}
            polylines={trailPath.length > 1 ? [{ id: 'latest-driver-trail', path: trailPath, color: '#16A34A' }] : []}
          >
            {data.trips.length === 0 ? (
              <div className="absolute inset-x-8 top-10 rounded-2xl bg-white/90 p-5 shadow-soft">
                <div className="font-black text-fleet-ink">No live trips right now</div>
                <p className="mt-1 text-sm font-semibold text-fleet-muted">Start a driver trip from the mobile app to publish GPS updates here.</p>
              </div>
            ) : (
              <div className="absolute left-5 top-5 rounded-2xl bg-white/95 p-4 text-xs font-bold shadow-soft ring-1 ring-fleet-line">
                <div className="text-fleet-blue">{latestTrip.routeCode}</div>
                <div className="mt-1 text-fleet-ink">{latestTrip.driverName}</div>
                <div className="text-fleet-muted">{latestTrip.latestLocation ? `${latestTrip.latestLocation.latitude.toFixed(4)}, ${latestTrip.latestLocation.longitude.toFixed(4)}` : 'Waiting for GPS'}</div>
              </div>
            )}
          </GoogleMapPanel>
        </Card>
        <aside className="space-y-5">
          <Card title="Route Summary">
            <div className="mb-3 flex items-center gap-2"><StatusBadge tone="green">Live Operations</StatusBadge><span className="text-sm font-bold text-fleet-muted">Avg delay: {Number(data.summary.average_route_delay_probability ?? 0).toFixed(2)}</span></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-2xl bg-slate-50 p-4"><div className="text-xs font-black uppercase text-fleet-muted">ETA Today</div><div className="text-2xl font-black">{Math.round(Number(data.summary.total_predicted_eta_today ?? 0))}m</div></div>
              <div className="rounded-2xl bg-slate-50 p-4"><div className="text-xs font-black uppercase text-fleet-muted">Delivered</div><div className="font-black">{Number(data.summary.delivered_orders_today ?? 0)}</div></div>
            </div>
          </Card>
          {latestTrip && (
            <Card title="Latest Active Driver">
              <div className="space-y-3 text-sm font-semibold">
                <div className="flex justify-between gap-3"><span className="text-fleet-muted">Route</span><span>{latestTrip.routeCode}</span></div>
                <div className="flex justify-between gap-3"><span className="text-fleet-muted">Driver</span><span>{latestTrip.driverName}</span></div>
                <div className="flex justify-between gap-3"><span className="text-fleet-muted">Vehicle</span><span>{latestTrip.vehicleCode}</span></div>
                <div className="flex justify-between gap-3"><span className="text-fleet-muted">Progress</span><span>{latestTrip.progress.completedStops}/{latestTrip.progress.totalStops}</span></div>
                <div className="flex justify-between gap-3"><span className="text-fleet-muted">Last GPS</span><span>{latestTrip.latestLocation?.recordedAt ?? 'Waiting'}</span></div>
              </div>
            </Card>
          )}
          <Card action={<button className="text-xs font-black text-fleet-blue" type="button">View All</button>} title="Trip Log">
            {data.events.length === 0 ? <EmptyState title="No trip events" description="Trip start, delivery updates, and driver issues will appear here." /> : <div className="space-y-5">
              {data.events.map((event) => (
                <div className="flex gap-3" key={event.id}>
                  <RadioTower className={`mt-1 h-4 w-4 ${event.severity === 'warning' || event.severity === 'critical' ? 'text-fleet-red' : 'text-fleet-blue'}`} />
                  <div className="flex-1">
                    <div className="flex items-center justify-between"><div className={`font-black ${event.severity === 'warning' || event.severity === 'critical' ? 'text-fleet-red' : ''}`}>{event.title}</div><div className="text-xs font-bold text-fleet-muted">{event.time}</div></div>
                    <p className="text-sm font-medium text-fleet-muted">{event.description}</p>
                    {(event.severity === 'warning' || event.severity === 'critical') && <button className="mt-2 text-sm font-black text-fleet-blue" type="button">Review Route</button>}
                  </div>
                </div>
              ))}
            </div>}
          </Card>
        </aside>
      </div>
    </div>
  )
}
