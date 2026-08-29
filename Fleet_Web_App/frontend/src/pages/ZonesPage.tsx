import { Activity, CalendarDays, Layers3, Search, Truck, Upload } from 'lucide-react'
import { useMemo, useState } from 'react'
import { OpenStreetMapPanel } from '../components/OpenStreetMapPanel'
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, PrimaryButton, StatusBadge } from '../components/UI'
import { buildZoneSnapshots, forecastDates } from '../features/demand/forecastView'
import { useAsyncData } from '../hooks/useAsyncData'
import { forecastService } from '../services/forecastService'
import type { DemandForecast, DemandZone, RiskLevel } from '../types'

const tone: Record<RiskLevel, { color: string; fill: string; label: string }> = {
  low: { color: '#059669', fill: 'bg-emerald-500', label: 'Low' },
  medium: { color: '#2563eb', fill: 'bg-blue-600', label: 'Medium' },
  high: { color: '#d97706', fill: 'bg-amber-500', label: 'High' },
  critical: { color: '#dc2626', fill: 'bg-red-600', label: 'Very high' },
}

export function ZonesPage() {
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [selectedDate, setSelectedDate] = useState('')
  const [importing, setImporting] = useState(false)
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [operationalZones, comparison] = await Promise.all([
      forecastService.getOperationalZones(),
      forecastService.getForecastVsActual(),
    ])
    return { operationalZones, comparison }
  }, [])

  const dates = useMemo(() => forecastDates(data?.comparison ?? []), [data?.comparison])
  const activeDate = selectedDate || dates[0] || ''
  const allZones = useMemo(() => buildZoneSnapshots(data?.operationalZones ?? [], data?.comparison ?? [], activeDate), [activeDate, data?.comparison, data?.operationalZones])
  const zones = useMemo(() => allZones.filter((zone) => zone.name.toLowerCase().includes(query.trim().toLowerCase())), [allZones, query])
  const selected = zones.find((zone) => zone.id === selectedId) ?? zones[0]
  const selectedForecast = data?.comparison.find((item) => item.zoneId === selected?.id && item.date === activeDate)
  const zoneOptions = useMemo(() => new Map(data?.operationalZones.map((zone) => [zone.id, zone]) ?? []), [data?.operationalZones])
  const totalPredicted = allZones.reduce((sum, zone) => sum + zone.predicted, 0)
  const totalRequired = allZones.reduce((sum, zone) => sum + (zone.requiredVehicles ?? 0), 0)
  const pressureZones = allZones.filter((zone) => zone.risk === 'high' || zone.risk === 'critical').length

  const mapMarkers = zones.flatMap((zone) => {
    const option = zoneOptions.get(zone.id)
    if (!option || !Number.isFinite(option.latitude) || !Number.isFinite(option.longitude)) return []
    const actual = zone.actualAvailable ? `${Math.round(zone.actual)} recorded` : 'actual not recorded'
    return [{
      id: zone.id,
      label: zone.name.slice(0, 1).toUpperCase(),
      title: zone.name,
      subtitle: `${Math.round(zone.predicted)} forecast · ${actual} · ${zone.requiredVehicles ?? 0} vehicle(s)`,
      position: { latitude: option.latitude, longitude: option.longitude },
      color: tone[zone.risk].color,
    }]
  })
  const serviceCircles = zones.flatMap((zone) => {
    const option = zoneOptions.get(zone.id)
    if (!option || !Number.isFinite(option.latitude) || !Number.isFinite(option.longitude)) return []
    return [{
      id: `${zone.id}-service-area`,
      center: { latitude: option.latitude, longitude: option.longitude },
      radiusMeters: Math.min(3500, 1400 + zone.predicted * 80),
      color: tone[zone.risk].color,
      fillColor: tone[zone.risk].color,
      fillOpacity: zone.risk === 'critical' ? 0.22 : zone.risk === 'high' ? 0.17 : zone.risk === 'medium' ? 0.12 : 0.08,
      title: `${zone.name} demand halo`,
      subtitle: `${Math.round(zone.predicted)} forecast orders · ${tone[zone.risk].label} demand`,
    }]
  })

  const importData = async () => {
    setImporting(true)
    try { await forecastService.importArtifacts(); await reload() } finally { setImporting(false) }
  }

  if (loading) return <LoadingState label="Loading Colombo demand zones..." />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load demand zones'} onRetry={reload} />

  return <div>
    <PageHeader
      action={dates.length > 0 ? <label className="flex items-center gap-2 rounded-lg border border-fleet-line bg-white px-3 py-2 text-sm font-semibold shadow-sm"><CalendarDays className="h-4 w-4 text-fleet-muted" /><input aria-label="Zone forecast date" className="outline-none" max={dates.at(-1)} min={dates[0]} onChange={(event) => setSelectedDate(event.target.value)} type="date" value={activeDate} /></label> : undefined}
      description="Compare parcel pressure and required fleet capacity across 15 Colombo operational zones."
      title="Colombo Demand Network"
    />

    {data.comparison.length === 0 && <div className="mb-5"><EmptyStateWithImport importing={importing} onImport={importData} /></div>}
    {data.operationalZones.length > 0 && <>
      <div className="mb-5 grid min-w-0 gap-4 sm:grid-cols-2 2xl:grid-cols-4">
        <Summary icon={Activity} label="Forecast orders" value={Math.round(totalPredicted).toLocaleString()} />
        <Summary icon={Layers3} label="Operational zones" value={String(allZones.length)} />
        <Summary icon={Truck} label="Required vehicle shifts" value={String(totalRequired)} />
        <Summary icon={Activity} label="High-pressure zones" value={String(pressureZones)} />
      </div>

      <div className="grid min-w-0 gap-5 2xl:grid-cols-[minmax(0,1.45fr)_360px]">
        <section className="min-w-0 overflow-hidden rounded-lg border border-fleet-line bg-white shadow-card">
          <div className="flex min-w-0 flex-wrap items-center gap-3 border-b border-fleet-line px-5 py-4">
            <div className="flex min-w-0 basis-full items-center gap-2 rounded-lg border border-fleet-line bg-slate-50 px-3 py-2 sm:basis-auto sm:flex-1"><Search className="h-4 w-4 shrink-0 text-fleet-muted" /><input aria-label="Search zones" className="min-w-0 w-full bg-transparent text-sm outline-none" onChange={(event) => setQuery(event.target.value)} placeholder="Search Colombo zones" value={query} /></div>
            <div className="flex flex-wrap gap-2">{(['low', 'medium', 'high', 'critical'] as RiskLevel[]).map((risk) => <span className="flex items-center gap-1.5 text-xs font-semibold text-fleet-muted" key={risk}><i className={`h-2.5 w-2.5 rounded-full ${tone[risk].fill}`} />{tone[risk].label}</span>)}</div>
          </div>
          <OpenStreetMapPanel circles={serviceCircles} className="min-h-[390px] rounded-none border-0 sm:min-h-[560px]" markers={mapMarkers} onCircleSelect={(circle) => setSelectedId(circle.id.replace('-service-area', ''))} onMarkerSelect={(marker) => setSelectedId(marker.id)} zoom={11}>
            <div className="absolute bottom-5 left-5 max-w-[calc(100%-2.5rem)] rounded-lg border border-white/80 bg-white/90 px-4 py-3 text-xs font-medium text-fleet-muted shadow-lg backdrop-blur"><strong className="block text-fleet-ink">Demand for {activeDate || 'selected date'}</strong>Marker color and halo size show the forecast demand level and volume.</div>
          </OpenStreetMapPanel>
        </section>
        <aside className="min-w-0 space-y-5"><Card title="Selected Zone">{selected ? <ZoneDetail forecast={selectedForecast} forecastDate={activeDate} zone={selected} /> : <p className="text-sm text-fleet-muted">No zone matches your search.</p>}</Card><PrimaryButton disabled={importing} onClick={importData}><Upload className="h-4 w-4" />{importing ? 'Updating...' : 'Update Forecast Data'}</PrimaryButton></aside>
      </div>
    </>}
  </div>
}

function Summary({ icon: Icon, label, value }: { icon: typeof Activity; label: string; value: string }) {
  return <div className="flex min-w-0 items-center gap-4 rounded-lg border border-fleet-line bg-white p-5 shadow-card"><span className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-emerald-50 text-emerald-700"><Icon className="h-5 w-5" /></span><div className="min-w-0"><div className="break-words text-xs font-semibold uppercase text-fleet-muted">{label}</div><div className="mt-1 text-2xl font-bold">{value}</div></div></div>
}

function ZoneDetail({ zone, forecast, forecastDate }: { zone: DemandZone; forecast?: DemandForecast; forecastDate: string }) {
  const range = forecast?.lowerBound == null || forecast.upperBound == null ? 'Not available' : `${Math.round(forecast.lowerBound)}-${Math.round(forecast.upperBound)}`
  return <div><div className="flex items-start justify-between gap-3"><div><div className="text-xl font-bold">{zone.name}</div><div className="mt-1 text-xs text-fleet-muted">{forecastDate || 'No forecast date'}</div></div><StatusBadge tone={zone.risk === 'critical' ? 'red' : zone.risk === 'high' ? 'amber' : zone.risk === 'medium' ? 'blue' : 'green'}>{tone[zone.risk].label}</StatusBadge></div><dl className="mt-5 grid grid-cols-2 gap-3"><Detail label="Forecast orders" value={Math.round(zone.predicted).toLocaleString()} /><Detail label="Required vehicles" value={String(zone.requiredVehicles ?? 0)} /><Detail label="Recorded orders" value={zone.actualAvailable ? Math.round(zone.actual).toLocaleString() : 'Not recorded'} /><Detail label="Forecast range" value={range} /></dl>{forecast?.action && <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3 text-sm font-semibold text-blue-800">{forecast.action}</div>}</div>
}

function Detail({ label, value }: { label: string; value: string }) { return <div className="min-w-0 rounded-lg bg-slate-50 p-3"><dt className="text-xs font-semibold text-fleet-muted">{label}</dt><dd className="mt-1 break-words text-lg font-bold">{value}</dd></div> }
function EmptyStateWithImport({ importing, onImport }: { importing: boolean; onImport: () => void }) { return <div className="rounded-lg border border-dashed border-fleet-line bg-white p-10 text-center shadow-card"><EmptyState description="Load the approved forecast package to populate Colombo operational zones." title="No demand forecast available" /><div className="mt-5 inline-flex"><PrimaryButton disabled={importing} onClick={onImport}><Upload className="h-4 w-4" />{importing ? 'Importing...' : 'Import Forecast Data'}</PrimaryButton></div></div> }
