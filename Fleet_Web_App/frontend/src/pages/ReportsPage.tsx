import { Download } from 'lucide-react'
import { Card, DataTable, ErrorState, LoadingState, MetricCard, OperationalInfo, PageHeader, PrimaryButton, StatusBadge } from '../components/UI'
import { BarChart3, Route, Wrench } from 'lucide-react'
import { useAsyncData } from '../hooks/useAsyncData'
import { modelStatusFromAvailability } from '../services/adapters'
import { fleetService } from '../services/fleetService'
import { forecastService } from '../services/forecastService'
import { operationsService } from '../services/operationsService'
import { reportService } from '../services/reportService'
import { saveDownload } from '../utils/download'
import { useDateRange } from '../hooks/useDateRange'
import { useState } from 'react'

export function ReportsPage() {
  const range = useDateRange()
  const [exporting, setExporting] = useState<'pdf' | 'xlsx' | null>(null)
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [predictive, demand, route] = await Promise.all([
      fleetService.getPredictiveModelStatus(),
      forecastService.getModelStatus(),
      operationsService.getRouteModelStatus(),
    ])
    return { predictive, demand, route }
  }, [])

  if (loading) return <LoadingState />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load model reports'} onRetry={reload} />

  const runs = [
    ['PM-BACKEND', 'Predictive Maint.', modelStatusFromAvailability(data.predictive), String(data.predictive.required_features_count ?? '-'), String(data.predictive.loaded ?? false)],
    ['DF-BACKEND', 'Demand Forecaster', modelStatusFromAvailability(data.demand), String(data.demand.zones_count ?? '-'), String(data.demand.loaded ?? false)],
    ['RT-BACKEND', 'Route Optimizer', modelStatusFromAvailability(data.route), String(data.route.feature_count ?? '-'), String(data.route.loaded ?? false)],
  ]
  const exportReport = async (format: 'pdf' | 'xlsx') => {
    setExporting(format)
    try {
      const file = await reportService.export(format, range.start || undefined, range.end || undefined)
      saveDownload(file.blob, file.filename)
    } finally {
      setExporting(null)
    }
  }

  return (
    <div>
      <PageHeader
        action={<div className="flex flex-wrap items-center gap-2"><OperationalInfo title="Model quality guidance">These cards report loaded backend artifacts. Loaded status does not guarantee production accuracy; RUL and graph-enhanced demand limitations remain documented.</OperationalInfo><PrimaryButton disabled={exporting !== null} onClick={() => exportReport('pdf')}><Download className="h-4 w-4" /> {exporting === 'pdf' ? 'Generating...' : 'PDF'}</PrimaryButton><PrimaryButton disabled={exporting !== null} onClick={() => exportReport('xlsx')}><Download className="h-4 w-4" /> {exporting === 'xlsx' ? 'Generating...' : 'Excel'}</PrimaryButton></div>}
        description="Review backend machine learning artifact status and dashboard readiness."
        title="Reports and Model Status"
      />
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard icon={Wrench} label="Maintenance Model" tone="green" trend={modelStatusFromAvailability(data.predictive)} value={String(data.predictive.required_features_count ?? 0)} />
        <MetricCard icon={Route} label="Route Model" tone="blue" trend={modelStatusFromAvailability(data.route)} value={String(data.route.feature_count ?? 0)} />
        <MetricCard icon={BarChart3} label="Demand Zones" tone="green" trend={modelStatusFromAvailability(data.demand)} value={String(data.demand.zones_count ?? 0)} />
      </div>
      <div className="mt-5">
        <Card title="Model Run History">
          <DataTable headers={['Run ID', 'Model Type', 'Status', 'Feature / Zone Count', 'Loaded']}>
            {runs.map((run) => (
              <tr key={run[0]}>
                {run.slice(0, 4).map((cell) => <td className="px-5 py-4 font-semibold" key={cell}>{cell}</td>)}
                <td className="px-5 py-4"><StatusBadge tone={run[4] === 'true' ? 'green' : 'amber'}>{run[4]}</StatusBadge></td>
              </tr>
            ))}
          </DataTable>
        </Card>
      </div>
    </div>
  )
}
