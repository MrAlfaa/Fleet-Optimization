import { AlertTriangle, CalendarDays, CheckCircle2, ShieldX, Truck } from 'lucide-react'
import { useState } from 'react'
import { Card, DataTable, EmptyState, ErrorState, LoadingState, MetricCard, OperationalInfo, PageHeader, RiskBadge, StatusBadge } from '../components/UI'
import { DEMAND_DATA_CONTEXT_NOTE, vehicleCategoryLabel } from '../data/sriLankaZones'
import { useAsyncData } from '../hooks/useAsyncData'
import { FleetCapacityVisualization } from '../features/readiness/FleetCapacityVisualization'
import { intelligenceService } from '../services/intelligenceService'

export function FleetReadinessPage() {
  const [forecastDate, setForecastDate] = useState('')
  const { data, error, loading, reload } = useAsyncData(
    () => intelligenceService.getFleetReadiness(forecastDate || undefined),
    [forecastDate],
  )

  if (loading) return <LoadingState label="Calculating fleet readiness..." />
  if (error || !data) return <ErrorState message={error ?? 'Unable to calculate fleet readiness'} onRetry={reload} />

  const activeStart = dateOnly(data.activeForecastRun?.forecast_start_date)
  const activeEnd = dateOnly(data.activeForecastRun?.forecast_end_date)
  const displayedForecastDate = forecastDate || data.forecastDate || activeStart

  return (
    <div>
      <PageHeader
        action={(
          <div className="flex items-center gap-2"><OperationalInfo title="Demand forecast context">{data.dataContextNote || DEMAND_DATA_CONTEXT_NOTE}</OperationalInfo><label className="flex items-center gap-2 rounded-lg border border-fleet-line bg-white px-3 py-2 text-sm font-semibold shadow-sm">
            <CalendarDays className="h-4 w-4 text-fleet-muted" />
            <input aria-label="Forecast date" className="outline-none" max={activeEnd || undefined} min={activeStart || undefined} onChange={(event) => setForecastDate(event.target.value)} type="date" value={displayedForecastDate} />
          </label></div>
        )}
        description="Combine forecast demand, vehicle health, predictive risk, and route activity before dispatch."
        title="Fleet Readiness"
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={Truck} label="Vehicles Required" tone="blue" trend={data.forecastDate ?? 'Latest forecast'} value={String(data.requiredVehicles)} />
        <MetricCard icon={CheckCircle2} label="Safe for Dispatch" tone="green" trend={`${data.warningVehicles} with warnings`} value={String(data.eligibleVehicles)} />
        <MetricCard icon={AlertTriangle} label="Capacity Gap" tone={data.capacityGap > 0 ? 'amber' : 'green'} trend="Required minus eligible" value={String(data.capacityGap)} />
        <MetricCard icon={ShieldX} label="Blocked Vehicles" tone={data.blockedVehicles > 0 ? 'red' : 'green'} trend={`${data.maintenanceVehicles} in maintenance`} value={String(data.blockedVehicles)} />
      </div>

      <FleetCapacityVisualization className="mt-5" readiness={data} />

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
        <Card title="Vehicle Dispatch Readiness">
          {data.vehicleReadiness.length === 0 ? <EmptyState title="No fleet vehicles" /> : (
            <DataTable headers={['Registration Number', 'Category', 'Operational', 'Health', 'Prediction', 'Readiness']}>
              {data.vehicleReadiness.map((vehicle) => (
                <tr key={vehicle.vehicleId}>
                  <td className="px-5 py-4"><div className="font-bold text-fleet-blue">{vehicle.registrationNumber}</div><div className="text-xs text-fleet-muted">{vehicle.vehicleCode}</div></td>
                  <td className="px-5 py-4">{vehicleCategoryLabel(vehicle.category)}</td>
                  <td className="px-5 py-4 capitalize">{vehicle.operationalStatus.replaceAll('_', ' ')}</td>
                  <td className="px-5 py-4 capitalize">{vehicle.healthStatus}</td>
                  <td className="px-5 py-4">{vehicle.predictionRisk ? <RiskBadge risk={vehicle.predictionRisk as 'low' | 'medium' | 'high' | 'critical'} /> : <StatusBadge tone="slate">No prediction</StatusBadge>}</td>
                  <td className="px-5 py-4"><StatusBadge tone={vehicle.readinessStatus === 'blocked' ? 'red' : vehicle.readinessStatus === 'warning' ? 'amber' : 'green'}>{vehicle.readinessStatus}</StatusBadge></td>
                </tr>
              ))}
            </DataTable>
          )}
        </Card>

        <div className="space-y-5">
          <Card title="High-demand Sri Lankan Zones">
            <div className="space-y-3">
              {data.highDemandZones.length === 0 ? <p className="text-sm text-fleet-muted">No high-demand zone for this forecast date.</p> : data.highDemandZones.map((zone) => (
                <div className="rounded-lg bg-slate-50 p-3" key={zone.operationalZoneId}>
                  <div className="font-bold">{zone.zoneDisplayName}</div>
                  <div className="mt-1 text-xs text-fleet-muted">{zone.demandLevel.replaceAll('_', ' ')} demand · {zone.estimatedRequiredVehicles} vehicle(s) · {Math.round(zone.predictedDemand)} orders</div>
                </div>
              ))}
            </div>
          </Card>
          <Card title="Operational Recommendations">
            <div className="space-y-3">
              {data.recommendations.length === 0 ? <p className="text-sm text-fleet-muted">No operational conflict detected.</p> : data.recommendations.map((item, index) => (
                <div className="rounded-lg border border-fleet-line p-3" key={`${item.type}-${index}`}>
                  <StatusBadge tone={item.severity === 'critical' ? 'red' : item.severity === 'high' ? 'amber' : 'blue'}>{item.type.replaceAll('_', ' ')}</StatusBadge>
                  <p className="mt-2 text-sm font-medium text-fleet-muted">{item.message}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

function dateOnly(value: string | null | undefined) {
  if (!value) return ''
  return value.includes('T') ? value.split('T', 1)[0] : value
}
