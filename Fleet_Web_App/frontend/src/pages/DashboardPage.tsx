import { AlertTriangle, Route, Truck, Wrench } from 'lucide-react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Line, LineChart } from 'recharts'
import { alerts, demandForecasts, routeTrend, vehicles } from '../data/mockData'
import { Card, MapPanel, MetricCard, PageHeader, StatusBadge } from '../components/UI'
import { formatNumber } from '../utils/format'

const riskProfile = [
  { name: 'Optimal', value: 65, color: '#1d4ed8' },
  { name: 'Watch', value: 25, color: '#64748b' },
  { name: 'Critical', value: 10, color: '#dc2626' },
]

export function DashboardPage() {
  return (
    <div>
      <PageHeader
        title="Dashboard Overview"
        description="Executive view of fleet health, demand load, dispatch activity, and active operational risk."
      />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={Truck} label="Active Vehicles" tone="blue" trend="+4.2%" value={formatNumber(1284)} />
        <MetricCard icon={Wrench} label="Under Maintenance" tone="amber" trend="-2" value="42" />
        <MetricCard icon={AlertTriangle} label="Critical Risk" tone="red" trend="+3" value="7" />
        <MetricCard icon={Route} label="Active Routes" tone="green" trend="+12.1%" value="315" />
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-[1.65fr_0.85fr]">
        <Card
          action={<button className="text-xs font-black text-fleet-blue" type="button">Expand Map</button>}
          title="Live Network Activity"
        >
          <MapPanel className="min-h-[310px]">
            <div className="absolute left-5 top-5 rounded-2xl bg-white/88 p-4 shadow-xl">
              <div className="text-xs font-black uppercase text-fleet-muted">Active routes</div>
              <div className="mt-1 text-3xl font-black">315</div>
            </div>
            {vehicles.slice(0, 3).map((vehicle, index) => (
              <div
                className="absolute rounded-xl bg-white/90 px-3 py-2 text-xs font-bold text-fleet-ink shadow"
                key={vehicle.id}
                style={{ left: `${28 + index * 18}%`, top: `${35 + index * 13}%` }}
              >
                {vehicle.number}
              </div>
            ))}
          </MapPanel>
        </Card>

        <Card title="Fleet Risk Profile">
          <div className="grid place-items-center">
            <ResponsiveContainer height={210} width="100%">
              <PieChart>
                <Pie data={riskProfile} dataKey="value" innerRadius={58} outerRadius={82} paddingAngle={4}>
                  {riskProfile.map((item) => (
                    <Cell fill={item.color} key={item.name} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="-mt-24 mb-14 text-center">
              <div className="text-3xl font-black">92</div>
              <div className="text-xs font-bold text-fleet-muted">Health Score</div>
            </div>
          </div>
          <div className="space-y-2">
            {riskProfile.map((item) => (
              <div className="flex items-center justify-between text-sm font-bold" key={item.name}>
                <span className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full" style={{ background: item.color }} />
                  {item.name}
                </span>
                <span>{item.value}%</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="mt-5 grid gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-1" title="Route Efficiency">
          <ResponsiveContainer height={230} width="100%">
            <LineChart data={routeTrend}>
              <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" />
              <XAxis dataKey="day" tickLine={false} />
              <YAxis tickLine={false} />
              <Tooltip />
              <Line dataKey="actual" stroke="#1d4ed8" strokeWidth={3} />
              <Line dataKey="planned" stroke="#94a3b8" strokeWidth={3} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Demand Forecast by Zone">
          <div className="space-y-3">
            {demandForecasts.map((forecast) => (
              <div className="flex items-center justify-between rounded-xl bg-slate-50 p-3" key={forecast.zone}>
                <div>
                  <div className="font-extrabold">{forecast.zone}</div>
                  <div className="text-xs font-semibold text-fleet-muted">{formatNumber(forecast.predictedVolume)} predicted</div>
                </div>
                <StatusBadge tone={forecast.variance > 20 ? 'red' : forecast.variance > 10 ? 'amber' : 'green'}>
                  {forecast.variance > 0 ? '+' : ''}{forecast.variance}%
                </StatusBadge>
              </div>
            ))}
          </div>
        </Card>
        <Card action={<StatusBadge tone="red">3 New</StatusBadge>} title="Active Alerts">
          <div className="space-y-3">
            {alerts.slice(0, 3).map((alert) => (
              <div className="rounded-xl border border-fleet-line bg-white p-3 shadow-sm" key={alert.id}>
                <div className="font-extrabold">{alert.title}</div>
                <p className="mt-1 text-sm font-medium text-fleet-muted">{alert.description}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
