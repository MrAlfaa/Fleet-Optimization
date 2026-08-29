import { CalendarDays, ChevronLeft, ChevronRight, Database, Download, History, Play, RefreshCcw, TrendingUp, Truck, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from '../components/ModalLayout'
import { Card, DataTable, EmptyState, ErrorState, LoadingState, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { aggregateForecastTrend, limitForecastDates } from '../features/demand/forecastView'
import { useAsyncData } from '../hooks/useAsyncData'
import { useDateRange } from '../hooks/useDateRange'
import { forecastService } from '../services/forecastService'
import type { DemandForecast, DemandForecastHorizon, DemandForecastRefreshResponse, DemandForecastRun, DemandForecastRunDetail, DemandLevel } from '../types'
import { saveDownload } from '../utils/download'
import { authService } from '../services/authService'
import { canAccess } from '../utils/permissions'

const horizons: DemandForecastHorizon[] = [7, 14, 30]
const levelTone: Record<DemandLevel, 'green' | 'blue' | 'amber' | 'red'> = {
  low: 'green', medium: 'blue', high: 'amber', very_high: 'red',
}

type ActionNotice = { tone: 'success' | 'error'; message: string }

export function DemandForecastPage() {
  const currentUser = authService.getSession()
  const canGenerate = canAccess(currentUser, 'demand.refresh')
  const canExport = canAccess(currentUser, 'reports.export')
  const range = useDateRange()
  const [selectedZone, setSelectedZone] = useState('')
  const [selectedHorizon, setSelectedHorizon] = useState<DemandForecastHorizon>(30)
  const [exporting, setExporting] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [latestGeneration, setLatestGeneration] = useState<DemandForecastRefreshResponse | null>(null)
  const [notice, setNotice] = useState<ActionNotice | null>(null)
  const [page, setPage] = useState(1)

  const loadData = async () => {
    const [status, dashboard, forecasts, zones, recentRuns] = await Promise.all([
      forecastService.getModelStatus(),
      forecastService.getDashboardSummary(),
      forecastService.getForecastVsActual({ zone_id: selectedZone || undefined, start_date: range.start || undefined, end_date: range.end || undefined }),
      forecastService.getOperationalZones(),
      forecastService.listForecastRuns(10),
    ])
    const context = await forecastService.getOperationalContext(range.start || forecasts[0]?.date)
    return { status, dashboard, forecasts, zones, recentRuns, context }
  }

  const { data, error, loading, reload, setData } = useAsyncData(loadData, [range.start, range.end, selectedZone])
  const horizonForecasts = useMemo(() => limitForecastDates(data?.forecasts ?? [], selectedHorizon), [data?.forecasts, selectedHorizon])
  const displayedDates = useMemo(
    () => [...new Set(horizonForecasts.map((item) => item.date?.slice(0, 10)).filter((value): value is string => Boolean(value)))].sort(),
    [horizonForecasts],
  )
  const trend = useMemo(() => aggregateForecastTrend(horizonForecasts), [horizonForecasts])
  const pageSize = 50
  const totalPages = Math.max(1, Math.ceil(horizonForecasts.length / pageSize))
  const effectivePage = Math.min(page, totalPages)
  const visibleForecasts = horizonForecasts.slice((effectivePage - 1) * pageSize, effectivePage * pageSize)

  const refreshView = async () => {
    setRefreshing(true)
    setNotice(null)
    try {
      setData(await loadData())
      setNotice({ tone: 'success', message: 'Forecast view refreshed from current API data.' })
    } catch (error) {
      setNotice({ tone: 'error', message: error instanceof Error ? error.message : 'Unable to refresh the forecast view.' })
    } finally {
      setRefreshing(false)
    }
  }

  const generateForecast = async () => {
    setGenerating(true)
    setNotice(null)
    try {
      const result = await forecastService.generateForecast(selectedHorizon)
      setLatestGeneration(result)
      setData(await loadData())
      setConfirmOpen(false)
      setNotice({
        tone: 'success',
        message: result.reused_active_run
          ? `Approved forecast run reused for the ${selectedHorizon}-day horizon.`
          : `New approved forecast run activated for the ${selectedHorizon}-day horizon.`,
      })
    } catch (error) {
      setNotice({ tone: 'error', message: error instanceof Error ? error.message : 'Unable to generate the forecast.' })
    } finally {
      setGenerating(false)
    }
  }

  const exportForecast = async () => {
    setExporting(true)
    try {
      const file = await forecastService.exportForecast({
        zone_id: selectedZone || undefined,
        start_date: displayedDates[0] || range.start || undefined,
        end_date: displayedDates.at(-1) || range.end || undefined,
      })
      saveDownload(file.blob, file.filename)
    } finally { setExporting(false) }
  }

  if (loading) return <LoadingState label="Loading zone demand forecast..." />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load demand forecast data'} onRetry={reload} />

  const forecastReady = data.status.operational_state === 'ready' || data.status.loaded === true || data.status.available === true
  const highDemandZones = Number(data.dashboard.high_demand_zones ?? 0) + Number(data.dashboard.very_high_demand_zones ?? 0)

  return <div className="min-w-0 max-w-full">
    <PageHeader
      action={<div className="flex max-w-full flex-wrap gap-2">
        <SecondaryButton onClick={() => setHistoryOpen(true)}><History className="h-4 w-4" />Forecast History</SecondaryButton>
        {canExport && <SecondaryButton disabled={exporting} onClick={exportForecast}><Download className="h-4 w-4" />{exporting ? 'Preparing CSV...' : 'Export Forecast'}</SecondaryButton>}
        <SecondaryButton disabled={refreshing || generating} onClick={refreshView}><RefreshCcw className={`h-4 w-4 ${refreshing ? 'animate-spin motion-reduce:animate-none' : ''}`} />{refreshing ? 'Refreshing...' : 'Refresh View'}</SecondaryButton>
        {canGenerate && <PrimaryButton disabled={generating} onClick={() => setConfirmOpen(true)}><Play className="h-4 w-4" />{generating ? 'Generating...' : 'Generate Forecast'}</PrimaryButton>}
      </div>}
      description="Plan vehicle capacity using daily parcel demand across Colombo operational zones."
      eyebrow={<StatusBadge tone={forecastReady ? 'green' : 'amber'}>{forecastReady ? 'Forecast ready' : 'Forecast unavailable'}</StatusBadge>}
      title="Zone Demand Forecast"
    />

    {notice && <div aria-live="polite" className={`mb-5 rounded-lg border px-4 py-3 text-sm font-semibold ${notice.tone === 'error' ? 'border-red-200 bg-red-50 text-red-800' : 'border-emerald-200 bg-emerald-50 text-emerald-800'}`} role={notice.tone === 'error' ? 'alert' : 'status'}>{notice.message}</div>}

    <div className="mb-5 flex min-w-0 flex-wrap items-end gap-4 rounded-lg border border-fleet-line bg-white p-4 shadow-card">
      <label className="min-w-[min(220px,100%)] flex-1 text-xs font-semibold text-fleet-muted">Operational zone
        <select aria-label="Operational zone" className="mt-1.5 min-h-10 w-full rounded-lg border border-fleet-line bg-white px-3 text-sm font-semibold text-fleet-ink outline-none focus:border-blue-500" onChange={(event) => { setSelectedZone(event.target.value); setPage(1) }} value={selectedZone}>
          <option value="">All Colombo zones</option>
          {data.zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}
        </select>
      </label>
      <fieldset className="min-w-0">
        <legend className="mb-1.5 text-xs font-semibold text-fleet-muted">Display horizon</legend>
        <div className="inline-flex max-w-full overflow-hidden rounded-lg border border-fleet-line bg-slate-50 p-1">
          {horizons.map((days) => <label className={`cursor-pointer rounded-md px-3 py-2 text-sm font-semibold ${selectedHorizon === days ? 'bg-fleet-blue text-white shadow-sm' : 'text-fleet-muted hover:bg-white'}`} key={days}>
            <input checked={selectedHorizon === days} className="sr-only" name="forecast-horizon" onChange={() => { setSelectedHorizon(days); setPage(1) }} type="radio" />{days} days
          </label>)}
        </div>
      </fieldset>
      <div aria-live="polite" className="min-w-[min(260px,100%)] flex-1 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2">
        <div className="text-xs font-bold uppercase text-blue-700">Showing {selectedHorizon} forecast days</div>
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm font-semibold text-fleet-ink">
          <span>{displayedDates.length > 0 ? `${formatDateOnly(displayedDates[0])} to ${formatDateOnly(displayedDates.at(-1))}` : 'No dates available'}</span>
          <span className="text-fleet-muted">{horizonForecasts.length.toLocaleString()} forecast rows</span>
        </div>
      </div>
    </div>

    <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.7fr)]">
      <ActiveForecastPanel latestGeneration={latestGeneration} run={data.status.active_run} />
      <RecentForecastCycles runs={data.recentRuns.slice(0, 5)} />
    </div>

    <div className="mt-5 grid min-w-0 gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.8fr)]">
      <OperationalContext context={data.context} />
      <Card title="Capacity Outlook"><div className="space-y-3">
        <OutlookRow icon={TrendingUp} label="High-demand zones" tone={highDemandZones > 0 ? 'text-amber-700' : 'text-emerald-700'} value={String(highDemandZones)} />
        <OutlookRow icon={CalendarDays} label="Next 7 forecast days" tone="text-blue-700" value={Math.round(Number(data.dashboard.total_predicted_demand_next_7_days ?? 0)).toLocaleString()} />
        <OutlookRow icon={Truck} label="Required vehicle shifts" tone="text-fleet-ink" value={String(Number(data.dashboard.total_required_vehicles_next_7_days ?? 0))} />
      </div></Card>
    </div>

    <div className="mt-5 min-w-0"><Card title={`${selectedHorizon}-day Demand Trend`}>
      {trend.length === 0 ? <EmptyState title="No forecast rows in this range" description="Select a forecast date range or refresh the view." /> : <ResponsiveContainer height={290} width="100%"><AreaChart data={trend} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}><CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" /><XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 12, fontWeight: 500 }} tickLine={false} /><YAxis tick={{ fill: '#64748b', fontSize: 12, fontWeight: 500 }} tickLine={false} /><Tooltip /><Legend /><Area connectNulls={false} dataKey="actual" fill="#d1fae5" name="Recorded orders" stroke="#059669" strokeWidth={3} /><Area dataKey="predicted" fill="#bfdbfe" name="Forecast orders" stroke="#1d4ed8" strokeDasharray="9 5" strokeWidth={3} /></AreaChart></ResponsiveContainer>}
    </Card></div>

    <section className="mt-5 min-w-0" aria-labelledby="forecast-details-title">
      <div className="mb-3 flex min-w-0 flex-wrap items-end justify-between gap-2">
        <div><h2 className="text-base font-bold text-fleet-ink" id="forecast-details-title">{selectedHorizon}-day Forecast Details</h2><p className="mt-0.5 text-xs font-medium text-fleet-muted">{displayedDates.length > 0 ? `${formatDateOnly(displayedDates[0])} to ${formatDateOnly(displayedDates.at(-1))}` : 'No dates available'}</p></div>
        <StatusBadge tone="blue">{horizonForecasts.length.toLocaleString()} rows</StatusBadge>
      </div>
      {horizonForecasts.length === 0 ? <EmptyState title="No forecast rows in this range" description="Select a packaged forecast date or refresh the view." /> : <><DataTable headers={['Date', 'Zone', 'Recorded Orders', 'Forecast', 'Forecast Range', 'Variance', 'Demand Level', 'Required Fleet', 'Operational Action']}>{visibleForecasts.map((forecast) => <ForecastRow forecast={forecast} key={`${forecast.zoneId}-${forecast.date}`} />)}</DataTable><div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm font-semibold text-fleet-muted"><span>Showing {(effectivePage - 1) * pageSize + 1}-{Math.min(effectivePage * pageSize, horizonForecasts.length)} of {horizonForecasts.length} forecast rows</span><div className="flex flex-wrap gap-2"><SecondaryButton disabled={effectivePage === 1} onClick={() => setPage((value) => Math.max(1, value - 1))}><ChevronLeft className="h-4 w-4" />Previous</SecondaryButton><SecondaryButton disabled={effectivePage === totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))}>Next<ChevronRight className="h-4 w-4" /></SecondaryButton></div></div></>}
    </section>

    {confirmOpen && <GenerateConfirmationDialog generating={generating} horizon={selectedHorizon} onCancel={() => setConfirmOpen(false)} onConfirm={generateForecast} />}
    {historyOpen && <ForecastHistoryDialog activeRunId={data.status.active_run?.model_run_id ?? null} onClose={() => setHistoryOpen(false)} runs={data.recentRuns} />}
  </div>
}

function GenerateConfirmationDialog({ generating, horizon, onCancel, onConfirm }: { generating: boolean; horizon: DemandForecastHorizon; onCancel: () => void; onConfirm: () => void }) {
  return <ModalViewport><ModalPanel aria-labelledby="generate-forecast-title" className="max-w-lg" role="dialog">
    <ModalHeader><h2 className="text-lg font-bold text-fleet-ink" id="generate-forecast-title">Generate forecast</h2></ModalHeader>
    <ModalBody><p className="text-sm leading-6 text-fleet-muted">Generate or reuse the approved {horizon}-day forecast cycle. The selected horizon does not run until you confirm.</p></ModalBody>
    <ModalFooter><SecondaryButton disabled={generating} onClick={onCancel}>Cancel</SecondaryButton><PrimaryButton disabled={generating} onClick={onConfirm}><Play className="h-4 w-4" />{generating ? 'Generating...' : 'Generate Forecast'}</PrimaryButton></ModalFooter>
  </ModalPanel></ModalViewport>
}

function ActiveForecastPanel({ run, latestGeneration }: { run: DemandForecastRun | null; latestGeneration: DemandForecastRefreshResponse | null }) {
  if (!run) return <Card title="Active Forecast"><EmptyState title="No active forecast" description="Generate an approved forecast cycle to begin planning." /></Card>
  return <Card title="Active Forecast"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
    <RunDetail label="Forecast source" value={forecastSourceLabel(run)} />
    <RunDetail label="Approved planning window" value={`${formatDateOnly(run.forecast_start_date)} to ${formatDateOnly(run.forecast_end_date)}`} />
    <RunDetail label="Saved cycle horizon" value={`${run.horizon_days} days`} />
    <RunDetail label="Activated / generated" value={formatTimestamp(run.activated_at || run.generated_at)} />
    <RunDetail label="Forecast records" value={`${run.records_generated.toLocaleString()} records across ${run.zones_count} zones`} />
    <RunDetail label="Latest action" value={latestGeneration ? latestGeneration.reused_active_run ? 'Reused approved run' : 'Activated new run' : 'No action in this view'} />
  </div><p className="mt-4 rounded-lg border border-blue-100 bg-blue-50 px-4 py-3 text-sm font-semibold text-blue-900">This planning window was fixed when the cycle was generated. Refresh View reloads saved data without changing forecast values.</p></Card>
}

function RecentForecastCycles({ runs }: { runs: DemandForecastRun[] }) {
  return <Card title="Recent Forecast Cycles">{runs.length === 0 ? <p className="text-sm text-fleet-muted">No recent cycles available.</p> : <ol className="space-y-2">{runs.map((run) => <li className="flex min-w-0 items-center justify-between gap-3 rounded-lg border border-fleet-line bg-slate-50 px-3 py-2.5" key={run.model_run_id}><div className="min-w-0"><div className="truncate text-sm font-bold text-fleet-ink">{formatDateOnly(run.forecast_start_date)} to {formatDateOnly(run.forecast_end_date)}</div><div className="mt-0.5 text-xs text-fleet-muted">{run.horizon_days} days · {run.records_generated.toLocaleString()} records</div></div><History className="h-4 w-4 shrink-0 text-fleet-blue" /></li>)}</ol>}</Card>
}

function ForecastHistoryDialog({ runs, activeRunId, onClose }: { runs: DemandForecastRun[]; activeRunId: string | null; onClose: () => void }) {
  const [detail, setDetail] = useState<DemandForecastRunDetail | null>(null)
  const [loadingRunId, setLoadingRunId] = useState<string | null>(null)
  const [loadError, setLoadError] = useState('')

  const loadRun = async (run: DemandForecastRun) => {
    setLoadingRunId(run.model_run_id)
    setLoadError('')
    try {
      setDetail(await forecastService.getForecastRun(run.model_run_id))
    } catch (error) {
      setDetail(null)
      setLoadError(error instanceof Error ? error.message : 'Unable to load the saved forecast cycle.')
    } finally {
      setLoadingRunId(null)
    }
  }

  return <ModalViewport><ModalPanel aria-labelledby="forecast-history-title" aria-modal="true" className="max-w-6xl" role="dialog">
    <ModalHeader className="flex items-start justify-between gap-4"><div><h2 className="text-xl font-extrabold text-fleet-ink" id="forecast-history-title">Forecast history</h2><p className="mt-1 text-sm text-fleet-muted">Review approved forecast cycles exactly as they were saved. History records cannot be edited.</p></div><button aria-label="Close forecast history" className="rounded-lg p-2 text-fleet-muted transition hover:bg-slate-100 hover:text-fleet-ink" onClick={onClose} title="Close" type="button"><X className="h-5 w-5" /></button></ModalHeader>
    <ModalBody className="grid min-w-0 gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
      <aside className="min-w-0"><h3 className="text-sm font-bold text-fleet-ink">Saved cycles</h3>{runs.length === 0 ? <p className="mt-3 text-sm text-fleet-muted">No saved forecast cycles are available.</p> : <div className="mt-3 space-y-2">{runs.map((run) => <button aria-label={`View forecast ${formatDateOnly(run.forecast_start_date)} to ${formatDateOnly(run.forecast_end_date)}`} className={`w-full rounded-lg border p-3 text-left transition hover:border-blue-300 hover:bg-blue-50 ${detail?.run.model_run_id === run.model_run_id ? 'border-blue-500 bg-blue-50' : 'border-fleet-line bg-white'}`} disabled={loadingRunId !== null} key={run.model_run_id} onClick={() => loadRun(run)} type="button"><div className="flex items-center justify-between gap-2"><span className="text-sm font-bold text-fleet-ink">{formatDateOnly(run.forecast_start_date)} to {formatDateOnly(run.forecast_end_date)}</span>{run.model_run_id === activeRunId && <StatusBadge tone="green">Active</StatusBadge>}</div><div className="mt-1 text-xs text-fleet-muted">{run.horizon_days} days · {run.records_generated.toLocaleString()} records</div>{loadingRunId === run.model_run_id && <div className="mt-2 text-xs font-semibold text-fleet-blue">Loading saved records...</div>}</button>)}</div>}</aside>
      <section className="min-w-0"><h3 className="text-sm font-bold text-fleet-ink">Saved forecast records</h3>{loadError && <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700" role="alert">{loadError}</div>}{!detail && !loadError ? <div className="mt-3"><EmptyState title="Select a forecast cycle" description="Choose a saved cycle to view its database records." /></div> : detail && <><div className="my-3 grid gap-3 sm:grid-cols-3"><RunDetail label="Planning window" value={`${formatDateOnly(detail.run.forecast_start_date)} to ${formatDateOnly(detail.run.forecast_end_date)}`} /><RunDetail label="Saved records" value={detail.total.toLocaleString()} /><RunDetail label="Generated" value={formatTimestamp(detail.run.activated_at || detail.run.generated_at)} /></div><DataTable headers={['Date', 'Zone', 'Forecast', 'Demand Level', 'Required Fleet']}>{detail.items.map((forecast) => <tr key={`${forecast.zoneId}-${forecast.date}`}><td className="px-5 py-3 font-semibold">{forecast.date}</td><td className="px-5 py-3 font-semibold text-fleet-blue">{forecast.zone}</td><td className="px-5 py-3 font-bold">{forecast.predictedVolume.toLocaleString()}</td><td className="px-5 py-3"><StatusBadge tone={levelTone[forecast.demandLevel ?? 'low']}>{(forecast.demandLevel ?? 'low').replaceAll('_', ' ')}</StatusBadge></td><td className="px-5 py-3 font-semibold">{forecast.requiredVehicles ?? 0}</td></tr>)}</DataTable></>}</section>
    </ModalBody>
    <ModalFooter><SecondaryButton onClick={onClose}>Close</SecondaryButton></ModalFooter>
  </ModalPanel></ModalViewport>
}

function RunDetail({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0 rounded-lg border border-fleet-line bg-slate-50 p-3"><dt className="text-xs font-semibold text-fleet-muted">{label}</dt><dd className="mt-1 break-words text-sm font-bold text-fleet-ink">{value}</dd></div>
}

function formatDateOnly(value: string | null | undefined) {
  if (!value) return 'Not recorded'
  return value.includes('T') ? value.split('T', 1)[0] : value
}

function formatTimestamp(value: string | null | undefined) {
  if (!value) return 'Not recorded'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function forecastSourceLabel(run: DemandForecastRun) {
  if (run.fallback_used || run.effective_source === 'artifact_fallback') return 'Approved artifact fallback'
  if (run.effective_source === 'artifact') return 'Approved artifact import'
  return 'Approved forecast engine'
}

function ForecastRow({ forecast }: { forecast: DemandForecast }) {
  const level = forecast.demandLevel ?? 'low'
  const range = forecast.lowerBound == null || forecast.upperBound == null ? 'Not available' : `${Math.round(forecast.lowerBound)}-${Math.round(forecast.upperBound)}`
  const variance = forecast.varianceOrders == null ? 'Not available' : `${forecast.varianceOrders > 0 ? '+' : ''}${Math.round(forecast.varianceOrders)} orders`
  return <tr><td className="px-5 py-4 font-semibold">{forecast.date || 'Not recorded'}</td><td className="px-5 py-4 font-semibold text-fleet-blue">{forecast.zone}</td><td className="px-5 py-4">{forecast.actualAvailable ? forecast.currentVolume.toLocaleString() : <span className="text-fleet-muted">Not recorded</span>}</td><td className="px-5 py-4 font-bold">{forecast.predictedVolume.toLocaleString()}</td><td className="px-5 py-4">{range}</td><td className="px-5 py-4">{variance}</td><td className="px-5 py-4"><StatusBadge tone={levelTone[level]}>{level.replaceAll('_', ' ')}</StatusBadge></td><td className="px-5 py-4 font-semibold">{forecast.requiredVehicles ?? 0}</td><td className="max-w-xs px-5 py-4 font-medium text-fleet-blue">{forecast.action}</td></tr>
}

function OutlookRow({ icon: Icon, label, tone, value }: { icon: typeof Truck; label: string; tone: string; value: string }) {
  return <div className="flex items-center justify-between gap-4 rounded-lg border border-fleet-line bg-slate-50 px-3 py-3"><span className="flex min-w-0 items-center gap-2 text-sm font-semibold text-fleet-muted"><Icon className={`h-4 w-4 shrink-0 ${tone}`} />{label}</span><strong className="shrink-0 text-lg text-fleet-ink">{value}</strong></div>
}

export interface OperationalContextData { date: string; holiday_name: string | null; is_holiday: boolean; rain_probability: number | null; weather_label: string; artifact_source: string; last_refresh_at: string | null }

export function OperationalContext({ context }: { context: OperationalContextData }) {
  const items = [
    { icon: CalendarDays, label: 'Forecast date', value: context.date },
    { icon: CalendarDays, label: 'Sri Lanka calendar', value: context.is_holiday ? context.holiday_name || 'Public holiday' : 'Regular operational day' },
    { icon: Database, label: 'Forecast source', value: context.artifact_source },
  ]
  return <Card title="Operational Context"><div className="grid gap-3 sm:grid-cols-2">{items.map(({ icon: Icon, label, value }) => <div className="min-w-0 rounded-lg border border-fleet-line bg-slate-50 p-3" key={label}><div className="flex items-center gap-2 text-xs font-semibold uppercase text-fleet-muted"><Icon className="h-4 w-4 shrink-0" />{label}</div><div className="mt-2 break-words font-bold text-fleet-ink">{value}</div></div>)}</div>{context.last_refresh_at && <div className="mt-3 text-xs text-fleet-muted">Last updated {new Date(context.last_refresh_at).toLocaleString()}</div>}</Card>
}
