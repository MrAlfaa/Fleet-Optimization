import { CalendarDays, CloudRain, Database, Download, RefreshCcw, TriangleAlert } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, DataTable, ErrorState, LoadingState, PageHeader, PrimaryButton, StatusBadge } from '../components/UI'
import { useAsyncData } from '../hooks/useAsyncData'
import { modelStatusFromAvailability } from '../services/adapters'
import { forecastService } from '../services/forecastService'
import { useDateRange } from '../hooks/useDateRange'
import { saveDownload } from '../utils/download'
import { useState } from 'react'

export function DemandForecastPage() {
  const range = useDateRange()
  const [exporting, setExporting] = useState(false)
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [status, dashboard, forecasts, trend, context] = await Promise.all([
      forecastService.getModelStatus(),
      forecastService.getDashboardSummary(),
      forecastService.getForecastVsActual({ start_date: range.start || undefined, end_date: range.end || undefined }),
      forecastService.getForecastVsActual({ start_date: range.start || undefined, end_date: range.end || undefined }).then((items) => items.slice(0, 7).map((item, index) => ({ day: `D${index + 1}`, actual: item.currentVolume, predicted: item.predictedVolume }))),
      forecastService.getOperationalContext(range.start || undefined),
    ])
    return { status, dashboard, forecasts, trend, context }
  }, [range.start, range.end])

  const refresh = async () => {
    await forecastService.refreshForecast(30, 'model')
    await reload()
  }

  const exportForecast = async () => {
    setExporting(true)
    try {
      const file = await forecastService.exportForecast({ start_date: range.start || undefined, end_date: range.end || undefined })
      saveDownload(file.blob, file.filename)
    } finally {
      setExporting(false)
    }
  }

  if (loading) return <LoadingState />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load demand forecast data'} onRetry={reload} />

  const statusLabel = modelStatusFromAvailability(data.status)
  const highDemandZones = Number(data.dashboard.high_demand_zones ?? 0) + Number(data.dashboard.very_high_demand_zones ?? 0)

  return (
    <div>
      <PageHeader
        action={<div className="flex flex-wrap gap-2"><PrimaryButton disabled={exporting} onClick={exportForecast}><Download className="h-4 w-4" /> {exporting ? 'Preparing CSV...' : 'Export Forecast'}</PrimaryButton><PrimaryButton onClick={refresh}><RefreshCcw className="h-4 w-4" /> Refresh Artifact</PrimaryButton></div>}
        description="Compare mapped Olist forecasts with live Sri Lankan delivery demand and safe local calibration."
        eyebrow={<StatusBadge tone={statusLabel === 'Loaded' || statusLabel === 'Available' ? 'green' : 'amber'}>{statusLabel}</StatusBadge>}
        title="Demand Forecast Dashboard"
      />
      <div className="grid gap-5 xl:grid-cols-[1.6fr_0.8fr]">
        <OperationalContext context={data.context} />
        <Card title="Overloaded Zone Detection">
          <div className="space-y-3">
            <div className="flex items-start gap-2 text-sm font-semibold leading-5 text-red-700"><TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" /> Backend detected {highDemandZones} high-demand zone{highDemandZones === 1 ? '' : 's'}.</div>
            <div className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm font-medium text-red-700"><span>Next 7 days demand</span><strong>{Math.round(Number(data.dashboard.total_predicted_demand_next_7_days ?? 0))}</strong></div>
            <div className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5 text-sm font-medium text-amber-700"><span>Required vehicles</span><strong>{Number(data.dashboard.total_required_vehicles_next_7_days ?? 0)}</strong></div>
          </div>
        </Card>
      </div>
      <div className="mt-5">
        <Card title="Daily / Weekly Trends">
          <ResponsiveContainer height={290} width="100%">
            <AreaChart data={data.trend} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
              <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" />
              <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 12, fontWeight: 500 }} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 12, fontWeight: 500 }} tickLine={false} />
              <Tooltip />
              <Legend />
              <Area dataKey="actual" fill="#94a3b8" stroke="#64748b" strokeWidth={3} />
              <Area dataKey="predicted" fill="#bfdbfe" stroke="#1d4ed8" strokeDasharray="9 5" strokeWidth={4} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <div className="mt-5">
        <DataTable headers={['Zone', 'Live actual', 'Raw mapped', 'Final forecast', 'Calibration', 'Recommended Action']}>
          {data.forecasts.map((forecast) => (
            <tr key={`${forecast.zone}-${forecast.predictedVolume}`}>
              <td className="px-5 py-4 font-semibold">{forecast.zone}</td>
              <td className="px-5 py-4">{forecast.currentVolume.toLocaleString()}</td>
              <td className="px-5 py-4">{Math.round(forecast.rawMappedForecast ?? forecast.predictedVolume).toLocaleString()}</td>
              <td className="px-5 py-4 font-semibold">{forecast.predictedVolume.toLocaleString()}</td>
              <td className="px-5 py-4"><StatusBadge tone={forecast.calibrationStatus === 'active' ? 'green' : 'amber'}>{forecast.calibrationStatus === 'active' ? `${forecast.calibrationFactor?.toFixed(2)}× calibrated` : `${forecast.historyDays ?? 0}/30 days`}</StatusBadge></td>
              <td className="px-5 py-4 font-medium text-fleet-blue">{forecast.action}</td>
            </tr>
          ))}
        </DataTable>
      </div>
    </div>
  )
}

export interface OperationalContextData { date: string; holiday_name: string | null; is_holiday: boolean; rain_probability: number | null; weather_label: string; artifact_source: string; last_refresh_at: string | null }

export function OperationalContext({ context }: { context: OperationalContextData }) {
  const items = [
    { icon: CalendarDays, label: 'Forecast date', value: context.date },
    { icon: CalendarDays, label: 'Sri Lanka calendar', value: context.is_holiday ? context.holiday_name || 'Public holiday' : 'Regular operational day' },
    { icon: CloudRain, label: 'Rain probability', value: context.rain_probability === null ? 'Unavailable' : `${Math.round(context.rain_probability)}%` },
    { icon: Database, label: 'Forecast source', value: context.artifact_source },
  ]
  return <Card title="Operational Context"><div className="grid gap-3 sm:grid-cols-2">{items.map(({ icon: Icon, label, value }) => <div className="rounded-lg border border-fleet-line bg-slate-50 p-3" key={label}><div className="flex items-center gap-2 text-xs font-semibold uppercase text-fleet-muted"><Icon className="h-4 w-4" />{label}</div><div className="mt-2 font-bold text-fleet-ink">{value}</div></div>)}</div>{context.last_refresh_at && <div className="mt-3 text-xs text-fleet-muted">Last refreshed {new Date(context.last_refresh_at).toLocaleString()}</div>}</Card>
}
