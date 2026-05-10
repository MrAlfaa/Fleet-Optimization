import { Download, Gauge, HeartPulse, ShieldCheck, TriangleAlert, Zap } from 'lucide-react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card, DataTable, MetricCard, PageHeader, PrimaryButton, RiskBadge, StatusBadge } from '../components/UI'
import { vehicles } from '../data/mockData'

const probability = [
  { component: 'Powertrain', value: 82 },
  { component: 'Electrical', value: 46 },
  { component: 'HVAC', value: 24 },
  { component: 'Brakes', value: 68 },
  { component: 'Suspension', value: 18 },
]

export function PredictiveRiskPage() {
  return (
    <div>
      <PageHeader
        action={<div className="flex gap-3"><PrimaryButton><Download className="h-4 w-4" /> Export Report</PrimaryButton><PrimaryButton><Zap className="h-4 w-4" /> Run Diagnostics</PrimaryButton></div>}
        description="Baseline Model Status: Placeholder baseline. Last updated 2 mins ago."
        eyebrow={<StatusBadge tone="green">Placeholder baseline</StatusBadge>}
        title="Predictive Risk Dashboard"
      />
      <div className="grid gap-4 lg:grid-cols-4">
        <MetricCard icon={TriangleAlert} label="Critical Risk Vehicles" tone="red" trend="+3 vs last week" value="14" />
        <MetricCard icon={HeartPulse} label="Overall Fleet Health" tone="green" trend="0% vs last week" value="82%" />
        <MetricCard icon={ShieldCheck} label="Prevented Breakdowns" tone="green" trend="+12 this month" value="47" />
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-red-700 shadow-card">
          <div className="mb-3 flex items-center gap-2 font-black"><Gauge className="h-5 w-5" /> Dispatch Warning</div>
          <p className="text-sm font-semibold">3 vehicles currently assigned to Zone 4 have high transmission failure probability within next 100 miles.</p>
        </div>
      </div>
      <div className="mt-5 grid gap-5 xl:grid-cols-[1.25fr_0.9fr]">
        <Card title="Component Failure Probability (30 Days)">
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
            {['CAB-1028 Engine Timing', 'VAN-3810 Brake Pad Wear', 'TRK-2041 Transmission Fluid'].map((item, index) => (
              <div className="flex items-center justify-between rounded-xl bg-slate-50 p-4" key={item}>
                <div><div className="font-extrabold">{item}</div><div className="text-xs font-bold text-fleet-muted">{94 - index * 7}% confidence</div></div>
                <div className="font-black text-fleet-blue">{index === 0 ? 'Tomorrow' : `Oct ${24 + index}`}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <div className="mt-5">
        <DataTable headers={['Asset ID', 'Predicted Failure', 'Severity', 'Probability', 'Est. Time to Failure', 'Assigned Route']}>
          {vehicles.map((vehicle, index) => (
            <tr key={vehicle.id}>
              <td className="px-5 py-4 font-black text-fleet-blue">{vehicle.number}</td>
              <td className="px-5 py-4 font-semibold">{['Coolant Leak', 'Alternator Output Low', 'DPF Filter Clogged', 'Tire Pressure Anomaly'][index]}</td>
              <td className="px-5 py-4"><RiskBadge risk={vehicle.risk} /></td>
              <td className="px-5 py-4 font-bold">{94 - index * 13}%</td>
              <td className="px-5 py-4 font-bold text-red-600">{index === 0 ? '< 24 Hours' : `${index + 1} - ${index + 3} Days`}</td>
              <td className="px-5 py-4">{vehicle.route ?? 'Unassigned'}</td>
            </tr>
          ))}
        </DataTable>
      </div>
    </div>
  )
}
