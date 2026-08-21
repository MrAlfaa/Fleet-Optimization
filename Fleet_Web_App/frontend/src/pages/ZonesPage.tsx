import { Activity, Layers3, MapPin, Search, Truck, Upload } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, PrimaryButton, StatusBadge } from '../components/UI'
import { SRI_LANKA_ZONES } from '../data/sriLankaZones'
import { useAsyncData } from '../hooks/useAsyncData'
import { forecastService } from '../services/forecastService'
import type { DemandZone, RiskLevel } from '../types'

const tone: Record<RiskLevel, { color: string; fill: string; label: string }> = {
  low: { color: '#059669', fill: 'bg-emerald-500', label: 'Low' },
  medium: { color: '#2563eb', fill: 'bg-blue-600', label: 'Medium' },
  high: { color: '#d97706', fill: 'bg-amber-500', label: 'High' },
  critical: { color: '#dc2626', fill: 'bg-red-600', label: 'Very high' },
}

function positionFor(zoneId: string) {
  const zone = SRI_LANKA_ZONES.find((item) => item.id === zoneId)
  if (!zone) return { left: 50, top: 50 }
  return { left: 28 + ((zone.longitude - 79.6) / 1.4) * 48, top: 88 - ((zone.latitude - 5.8) / 4.1) * 76 }
}

export function ZonesPage() {
  const [query, setQuery] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [importing, setImporting] = useState(false)
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [operationalZones, comparison, summary] = await Promise.all([forecastService.getOperationalZones(), forecastService.getForecastVsActual(), forecastService.getDashboardSummary()])
    return { operationalZones, comparison, summary }
  }, [])
  const zones = useMemo(() => (data?.operationalZones ?? []).map((zone) => {
    const records = (data?.comparison ?? []).filter((item) => item.zoneId === zone.id)
    const latest = records.at(-1)
    const predicted = latest?.predictedVolume ?? 0
    return { id: zone.id, name: zone.name, predicted, actual: latest?.currentVolume ?? 0, overloadScore: predicted, risk: predicted >= 80 ? 'critical' : predicted >= 50 ? 'high' : predicted >= 25 ? 'medium' : 'low' } as DemandZone
  }).filter((zone) => zone.name.toLowerCase().includes(query.toLowerCase())), [data?.comparison, data?.operationalZones, query])
  const selected = zones.find((zone) => zone.id === selectedId) ?? zones[0]
  const importData = async () => { setImporting(true); try { await forecastService.importArtifacts(); await reload() } finally { setImporting(false) } }

  if (loading) return <LoadingState label="Loading Sri Lanka demand zones..." />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load demand zones'} onRetry={reload} />

  return <div>
    <PageHeader description="Monitor predicted parcel demand and fleet capacity across Sri Lankan operational zones." title="Sri Lanka Demand Network" />
    {data.comparison.length === 0 && <div className="mb-5"><EmptyStateWithImport importing={importing} onImport={importData} /></div>}
    {data.operationalZones.length > 0 && <>
      <div className="mb-5 grid min-w-0 gap-4 sm:grid-cols-2 2xl:grid-cols-3">
        <Summary icon={Activity} label="Predicted demand · 7 days" value={Math.round(Number(data.summary.total_predicted_demand_next_7_days ?? 0)).toLocaleString()} />
        <Summary icon={Layers3} label="Operational zones" value={String(data.operationalZones.length)} />
        <Summary icon={Truck} label="Required vehicles" value={String(Number(data.summary.total_required_vehicles_next_7_days ?? 0))} />
      </div>
      <div className="grid min-w-0 gap-5 2xl:grid-cols-[minmax(0,1.45fr)_360px]">
        <section className="min-w-0 overflow-hidden rounded-lg border border-fleet-line bg-white shadow-card">
          <div className="flex flex-wrap items-center gap-3 border-b border-fleet-line px-5 py-4">
            <div className="flex min-w-0 basis-full items-center gap-2 rounded-lg border border-fleet-line bg-slate-50 px-3 py-2 sm:basis-auto sm:flex-1"><Search className="h-4 w-4 shrink-0 text-fleet-muted" /><input aria-label="Search zones" className="min-w-0 w-full bg-transparent text-sm outline-none" onChange={(event) => setQuery(event.target.value)} placeholder="Search Sri Lankan zones" value={query} /></div>
            <div className="flex flex-wrap gap-2">{(['low', 'medium', 'high', 'critical'] as RiskLevel[]).map((risk) => <span className="flex items-center gap-1.5 text-xs font-semibold text-fleet-muted" key={risk}><i className={`h-2.5 w-2.5 rounded-full ${tone[risk].fill}`} />{tone[risk].label}</span>)}</div>
          </div>
          <div className="relative min-h-[460px] overflow-hidden bg-[#eef6f5] sm:min-h-[620px]">
            <div className="absolute inset-0 opacity-40" style={{ backgroundImage: 'linear-gradient(#b9d8d2 1px,transparent 1px),linear-gradient(90deg,#b9d8d2 1px,transparent 1px)', backgroundSize: '42px 42px' }} />
            <svg aria-label="Sri Lanka operational demand map" className="absolute inset-0 h-full w-full" role="img" viewBox="0 0 700 760"><defs><linearGradient id="island" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stopColor="#dcefea" /><stop offset="1" stopColor="#b7d8cf" /></linearGradient><filter id="shadow"><feDropShadow dx="0" dy="10" floodColor="#0f766e" floodOpacity=".18" stdDeviation="12" /></filter></defs><path d="M370 38 C420 80 442 142 433 201 C425 252 455 302 479 354 C510 420 486 505 449 569 C415 628 393 704 337 726 C281 707 255 651 227 600 C193 537 173 474 190 407 C204 352 230 314 224 257 C218 197 249 124 292 77 C315 52 343 36 370 38Z" fill="url(#island)" filter="url(#shadow)" stroke="#5a9f91" strokeWidth="3" /><path d="M327 86 C361 127 369 175 358 223 M245 351 C310 334 388 352 452 397 M223 484 C296 466 378 488 450 538" fill="none" opacity=".45" stroke="#6fa99e" strokeDasharray="8 10" strokeWidth="2" /></svg>
            {zones.map((zone) => { const position = positionFor(zone.id); const radius = Math.max(28, Math.min(52, 26 + zone.predicted / 5)); return <button aria-label={`${zone.name}: ${zone.predicted} predicted demand`} className="absolute -translate-x-1/2 -translate-y-1/2 text-left" key={zone.id} onClick={() => setSelectedId(zone.id)} style={{ left: `${position.left}%`, top: `${position.top}%` }} title={zone.name} type="button"><span className={`absolute left-1/2 top-1/2 -z-10 -translate-x-1/2 -translate-y-1/2 rounded-full opacity-20 ${tone[zone.risk].fill} ${zone.risk === 'critical' || zone.risk === 'high' ? 'animate-ping motion-reduce:animate-none' : ''}`} style={{ height: radius * 2.3, width: radius * 2.3 }} /><span className="grid place-items-center rounded-full border-4 border-white text-white shadow-xl transition hover:scale-110" style={{ backgroundColor: tone[zone.risk].color, height: radius, width: radius }}><MapPin className="h-4 w-4" /></span>{selected?.id === zone.id && <span className="absolute left-1/2 top-full mt-2 -translate-x-1/2 whitespace-nowrap rounded-md bg-slate-950 px-2.5 py-1.5 text-xs font-semibold text-white shadow-xl">{zone.name}</span>}</button> })}
            <div className="absolute bottom-5 left-5 rounded-lg border border-white/80 bg-white/90 px-4 py-3 text-xs font-medium text-fleet-muted shadow-lg backdrop-blur"><strong className="block text-fleet-ink">Operational demand view</strong>Marker size represents forecast demand. Pulsing zones need capacity review.</div>
          </div>
        </section>
        <aside className="min-w-0 space-y-5"><Card title="Selected Zone">{selected ? <ZoneDetail zone={selected} /> : <p className="text-sm text-fleet-muted">No zone matches your search.</p>}</Card><PrimaryButton disabled={importing} onClick={importData}><Upload className="h-4 w-4" />{importing ? 'Importing...' : 'Refresh Artifact Data'}</PrimaryButton></aside>
      </div>
    </>}
  </div>
}

function Summary({ icon: Icon, label, value }: { icon: typeof Activity; label: string; value: string }) { return <div className="flex min-w-0 items-center gap-4 rounded-lg border border-fleet-line bg-white p-5 shadow-card"><span className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-emerald-50 text-emerald-700"><Icon className="h-5 w-5" /></span><div className="min-w-0"><div className="break-words text-xs font-semibold uppercase text-fleet-muted">{label}</div><div className="mt-1 text-2xl font-bold">{value}</div></div></div> }
function ZoneDetail({ zone }: { zone: DemandZone }) { const required = Math.max(1, Math.ceil(zone.predicted / 25)); return <div><div className="flex items-start justify-between gap-3"><div><div className="text-xl font-bold">{zone.name}</div><div className="mt-1 text-xs text-fleet-muted">{zone.id}</div></div><StatusBadge tone={zone.risk === 'critical' ? 'red' : zone.risk === 'high' ? 'amber' : zone.risk === 'medium' ? 'blue' : 'green'}>{tone[zone.risk].label}</StatusBadge></div><dl className="mt-5 grid grid-cols-2 gap-3"><Detail label="Final forecast" value={Math.round(zone.predicted).toLocaleString()} /><Detail label="Required vehicles" value={String(required)} /><Detail label="Live actual orders" value={Math.round(zone.actual).toLocaleString()} /><Detail label="Demand score" value={`${Math.round(zone.overloadScore)}%`} /></dl></div> }
function Detail({ label, value }: { label: string; value: string }) { return <div className="rounded-lg bg-slate-50 p-3"><dt className="text-xs font-semibold text-fleet-muted">{label}</dt><dd className="mt-1 text-lg font-bold">{value}</dd></div> }
function EmptyStateWithImport({ importing, onImport }: { importing: boolean; onImport: () => void }) { return <div className="rounded-lg border border-dashed border-fleet-line bg-white p-10 text-center shadow-card"><EmptyState description="Import the packaged demand artifacts to populate Sri Lankan operational zones." title="No demand zones imported" /><div className="mt-5 inline-flex"><PrimaryButton disabled={importing} onClick={onImport}><Upload className="h-4 w-4" />{importing ? 'Importing...' : 'Import Forecast Data'}</PrimaryButton></div></div> }
