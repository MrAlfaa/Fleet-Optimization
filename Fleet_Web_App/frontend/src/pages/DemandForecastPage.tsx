import { Download, SlidersHorizontal, TriangleAlert } from 'lucide-react'
import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useState } from 'react'
import { Card, DataTable, PageHeader, PrimaryButton, StatusBadge } from '../components/UI'
import { demandForecasts, demandTrend } from '../data/mockData'

export function DemandForecastPage() {
  const [rain, setRain] = useState(true)
  const [holiday, setHoliday] = useState(false)
  const [promotion, setPromotion] = useState(false)
  return (
    <div>
      <PageHeader
        action={<PrimaryButton><Download className="h-4 w-4" /> Export Forecast</PrimaryButton>}
        description="Forecast parcel demand per zone using a transparent placeholder moving-average baseline."
        eyebrow={<StatusBadge tone="blue">Placeholder moving average</StatusBadge>}
        title="Demand Forecast Dashboard"
      />
      <div className="grid gap-5 xl:grid-cols-[1.6fr_0.8fr]">
        <Card title="Simulation Controls">
          <div className="grid gap-4 md:grid-cols-4">
            <Toggle checked={holiday} label="Holiday" onChange={setHoliday} />
            <Toggle checked={rain} label="Rain Day" onChange={setRain} />
            <Toggle checked={promotion} label="Promotion" onChange={setPromotion} />
            <label className="text-sm font-bold text-fleet-muted">Manual Demand Spike (%)<input className="mt-2 min-h-11 w-full rounded-xl border border-fleet-line px-3 font-semibold outline-none focus:ring-4 focus:ring-blue-100" placeholder="e.g. 15" /></label>
          </div>
        </Card>
        <Card title="Overloaded Zone Detection">
          <div className="space-y-3 text-red-700">
            <div className="flex gap-2 font-extrabold"><TriangleAlert className="h-5 w-5" /> Simulation indicates capacity risk.</div>
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 font-bold">Colombo Central <span className="float-right">124% Cap</span></div>
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 font-bold text-amber-700">Nugegoda East <span className="float-right">95% Cap</span></div>
          </div>
        </Card>
      </div>
      <div className="mt-5">
        <Card title="Daily / Weekly Trends">
          <ResponsiveContainer height={290} width="100%">
            <AreaChart data={demandTrend}>
              <CartesianGrid strokeDasharray="4 4" stroke="#e2e8f0" />
              <XAxis dataKey="day" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Area dataKey="actual" fill="#94a3b8" stroke="#64748b" strokeWidth={3} />
              <Area dataKey="predicted" fill="#bfdbfe" stroke="#1d4ed8" strokeDasharray="9 5" strokeWidth={4} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      </div>
      <div className="mt-5">
        <DataTable headers={['Zone', 'Current Vol', 'Predicted Vol', 'Variance', 'Recommended Action']}>
          {demandForecasts.map((forecast) => (
            <tr key={forecast.zone}>
              <td className="px-5 py-4 font-black">{forecast.zone}</td>
              <td className="px-5 py-4">{forecast.currentVolume.toLocaleString()}</td>
              <td className="px-5 py-4 font-black">{forecast.predictedVolume.toLocaleString()}</td>
              <td className="px-5 py-4"><StatusBadge tone={forecast.variance > 20 ? 'red' : forecast.variance > 10 ? 'amber' : 'green'}>{forecast.variance > 0 ? '+' : ''}{forecast.variance}%</StatusBadge></td>
              <td className="px-5 py-4 font-bold text-fleet-blue">{forecast.action}</td>
            </tr>
          ))}
        </DataTable>
      </div>
    </div>
  )
}

function Toggle({ checked, label, onChange }: { checked: boolean; label: string; onChange: (value: boolean) => void }) {
  return (
    <button className="flex min-h-14 items-center justify-between rounded-2xl border border-fleet-line bg-slate-50 px-4 text-left font-bold" onClick={() => onChange(!checked)} type="button">
      <span className="flex items-center gap-2"><SlidersHorizontal className="h-4 w-4 text-fleet-muted" /> {label}</span>
      <span className={`h-6 w-11 rounded-full p-1 transition ${checked ? 'bg-fleet-blue' : 'bg-slate-300'}`}><span className={`block h-4 w-4 rounded-full bg-white transition ${checked ? 'translate-x-5' : ''}`} /></span>
    </button>
  )
}
