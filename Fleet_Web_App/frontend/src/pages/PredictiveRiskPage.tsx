import { Download, HeartPulse, ShieldCheck, TriangleAlert, Zap } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, DataTable, ErrorState, LoadingState, MetricCard, OperationalInfo, PageHeader, PrimaryButton, RiskBadge, StatusBadge } from '../components/UI'
import { useAsyncData } from '../hooks/useAsyncData'
import { modelStatusFromAvailability, toRiskLevel } from '../services/adapters'
import { fleetService } from '../services/fleetService'

type RecordLike = Record<string, unknown>

export function PredictiveRiskPage() {
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [status, summary, predictions, vehicles] = await Promise.all([
      fleetService.getPredictiveModelStatus(),
      fleetService.getFleetRiskSummary(),
      fleetService.listPredictions({ limit: 20 }),
      fleetService.listVehicles({ limit: 20 }),
    ])
    return { status, summary, predictions, vehicles }
  }, [])

  const runDiagnostics = async () => {
    const vehicle = data?.vehicles[0]
    if (!vehicle) return
    await fleetService.simulatePrediction(vehicle.id)
    await reload()
  }

  if (loading) return <LoadingState />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load predictive maintenance data'} onRetry={reload} />

  const statusLabel = modelStatusFromAvailability(data.status)
  const items = data.predictions.items as RecordLike[]
  const probability = items.slice(0, 6).map((item, index) => ({
    component: String(item.maintenance_type_name ?? item.part_name ?? `Prediction ${index + 1}`),
    value: Math.round(Number(item.failure_probability ?? 0) * 100),
  }))
  const criticalCount = Number(data.summary.critical_prediction_count ?? data.summary.critical ?? 0)
  const averageProbability = Math.round(Number(data.summary.average_failure_probability ?? 0) * 100)

  return (
    <div>
      <PageHeader
        action={<div className="flex gap-3"><OperationalInfo active={criticalCount > 0} severity={criticalCount > 0 ? 'critical' : 'info'} title="Dispatch risk guidance">High and critical predictions update vehicle health and create maintenance alerts. Critical vehicles must be inspected before dispatch.</OperationalInfo><PrimaryButton><Download className="h-4 w-4" /> Export Report</PrimaryButton><PrimaryButton onClick={runDiagnostics}><Zap className="h-4 w-4" /> Run Diagnostics</PrimaryButton></div>}
        description={`Predictive maintenance model status: ${statusLabel}.`}
        eyebrow={<StatusBadge tone={statusLabel === 'Loaded' || statusLabel === 'Available' ? 'green' : 'amber'}>{statusLabel}</StatusBadge>}
        title="Predictive Risk Dashboard"
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <MetricCard icon={TriangleAlert} label="Critical Risk Vehicles" tone="red" trend="Needs action" value={String(criticalCount)} />
        <MetricCard icon={HeartPulse} label="Average Failure Risk" tone="green" trend="Latest predictions" value={`${averageProbability}%`} />
        <MetricCard icon={ShieldCheck} label="Predictions Stored" tone="green" trend="Prediction history" value={String(data.predictions.total ?? items.length)} />
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-[1.25fr_0.9fr]">
        <Card title="Component Failure Probability">
          <ResponsiveContainer height={270} width="100%">
            <BarChart data={probability}>
              <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" />
              <XAxis dataKey="component" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#1d4ed8" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Optimal Maintenance Windows">
          <div className="space-y-3">
            {items.slice(0, 4).map((item) => (
              <div className="flex items-center justify-between rounded-xl bg-slate-50 p-4" key={String(item.id ?? item.prediction_id)}>
                <div><div className="font-extrabold">{String(item.maintenance_type_name ?? 'Maintenance inspection')}</div><div className="text-xs font-bold text-fleet-muted">{Math.round(Number(item.failure_probability ?? 0) * 100)}% probability</div></div>
                <div className="font-black text-fleet-blue">{item.next_maintenance_date ? new Date(String(item.next_maintenance_date)).toLocaleDateString() : 'Review'}</div>
              </div>
            ))}
            {items.length === 0 && <div className="text-sm font-bold text-fleet-muted">No predictions saved yet. Run diagnostics on a seeded vehicle.</div>}
          </div>
        </Card>
      </div>
      <div className="mt-5">
        <DataTable headers={['Vehicle ID', 'Predicted Failure', 'Severity', 'Probability', 'Est. Time to Failure', 'Prediction ID']}>
          {items.map((item) => (
            <tr key={String(item.id ?? item.prediction_id)}>
              <td className="px-5 py-4 font-black text-fleet-blue">{String(item.vehicle_id ?? '-')}</td>
              <td className="px-5 py-4 font-semibold">{String(item.maintenance_type_name ?? 'Unknown maintenance type')}</td>
              <td className="px-5 py-4"><RiskBadge risk={toRiskLevel(item.risk_level)} /></td>
              <td className="px-5 py-4 font-bold">{Math.round(Number(item.failure_probability ?? 0) * 100)}%</td>
              <td className="px-5 py-4 font-bold text-red-600">{item.predicted_rul ? `${Number(item.predicted_rul).toFixed(1)} ${String(item.rul_unit ?? '')}` : 'Not available'}</td>
              <td className="px-5 py-4">{String(item.id ?? item.prediction_id ?? '-')}</td>
            </tr>
          ))}
        </DataTable>
      </div>
    </div>
  )
}
