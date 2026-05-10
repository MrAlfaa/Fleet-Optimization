import { Download, Info } from 'lucide-react'
import { Card, DataTable, MetricCard, PageHeader, PrimaryButton, StatusBadge } from '../components/UI'
import { BarChart3, Route, Wrench } from 'lucide-react'

const runs = [
  ['ML-2026-10-A', 'Predictive Maint.', 'Oct 24, 14:30', 'Placeholder', '-', 'Completed'],
  ['ML-2026-10-B', 'Demand Forecaster', 'Oct 24, 10:15', 'Placeholder', '-', 'Completed'],
  ['ML-2026-10-C', 'Route Optimizer', 'Oct 23, 22:00', '-', '-', 'Ready'],
  ['ML-2026-09-D', 'Predictive Maint.', 'Oct 20, 08:00', 'Unavailable', '-', 'Needs Training'],
]

export function ReportsPage() {
  return (
    <div>
      <PageHeader
        action={<PrimaryButton><Download className="h-4 w-4" /> Export Report</PrimaryButton>}
        description="Review system analytics and machine learning placeholder status."
        title="Reports and Model Status"
      />
      <div className="mb-5 flex items-start gap-3 rounded-2xl border border-blue-200 bg-blue-50 p-4 text-blue-800">
        <Info className="mt-0.5 h-5 w-5" />
        <div><div className="font-black">Model Status Notice</div><div className="text-sm font-semibold">ML models are placeholders until trained with sufficient historical fleet data. Current metrics are UI placeholders only.</div></div>
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard icon={Wrench} label="Maintenance Readiness" tone="green" trend="Placeholder" value="94.2%" />
        <MetricCard icon={Route} label="Route Efficiency" tone="blue" trend="OR-Tools later" value="88.7%" />
        <MetricCard icon={BarChart3} label="Demand Accuracy" tone="green" trend="Placeholder" value="91.5%" />
      </div>
      <div className="mt-5">
        <Card title="Model Run History">
          <DataTable headers={['Run ID', 'Model Type', 'Timestamp', 'Metric State', 'RMSE', 'Status']}>
            {runs.map((run) => (
              <tr key={run[0]}>
                {run.slice(0, 5).map((cell) => <td className="px-5 py-4 font-semibold" key={cell}>{cell}</td>)}
                <td className="px-5 py-4"><StatusBadge tone={run[5] === 'Completed' ? 'green' : run[5] === 'Ready' ? 'blue' : 'amber'}>{run[5]}</StatusBadge></td>
              </tr>
            ))}
          </DataTable>
        </Card>
      </div>
    </div>
  )
}
