import { AlertCircle, Bell, CheckCircle2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { alerts as seedAlerts } from '../data/mockData'
import { Card, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import type { Alert } from '../types'

const filters = ['all', 'maintenance', 'route', 'demand', 'driver'] as const

export function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>(seedAlerts)
  const [filter, setFilter] = useState<(typeof filters)[number]>('all')
  const visible = useMemo(() => (filter === 'all' ? alerts : alerts.filter((alert) => alert.category === filter)), [alerts, filter])
  const acknowledge = (id: string) => setAlerts((items) => items.map((alert) => (alert.id === id ? { ...alert, acknowledged: true } : alert)))

  return (
    <div>
      <PageHeader
        description="Real-time system anomalies requiring attention."
        title="Alerts Center"
      />
      <div className="mb-4 flex flex-wrap gap-2">
        {filters.map((item) => (
          <button className={`rounded-xl px-4 py-2 text-sm font-extrabold capitalize ${filter === item ? 'bg-fleet-blue text-white' : 'bg-white text-fleet-muted ring-1 ring-fleet-line'}`} key={item} onClick={() => setFilter(item)} type="button">
            {item === 'all' ? 'All Filters' : item}
          </button>
        ))}
      </div>
      <div className="space-y-4">
        {(['critical', 'warning', 'info'] as const).map((severity) => {
          const group = visible.filter((alert) => alert.severity === severity)
          if (group.length === 0) return null
          return (
            <Card
              action={<StatusBadge tone={severity === 'critical' ? 'red' : severity === 'warning' ? 'amber' : 'blue'}>{group.filter((alert) => !alert.acknowledged).length} Active</StatusBadge>}
              className={severity === 'critical' ? 'border-red-200' : severity === 'warning' ? 'border-amber-200' : 'border-blue-200'}
              key={severity}
              title={severity === 'critical' ? 'Critical Integrity Alerts' : severity === 'warning' ? 'System Warnings' : 'Operational Info'}
            >
              <div className="divide-y divide-fleet-line">
                {group.map((alert) => (
                  <div className="flex flex-col gap-3 py-3 md:flex-row md:items-center" key={alert.id}>
                    <div className="flex items-center gap-3 md:w-48"><AlertIcon severity={alert.severity} /><span className="text-sm font-black">{alert.time}</span><StatusBadge tone="slate">{alert.vehicle}</StatusBadge></div>
                    <div className="flex-1"><div className="font-black">{alert.title}</div><p className="text-sm font-semibold text-fleet-muted">{alert.description}</p></div>
                    <div className="flex gap-2">
                      <SecondaryButton onClick={() => acknowledge(alert.id)}>{alert.acknowledged ? <CheckCircle2 className="h-4 w-4" /> : <Bell className="h-4 w-4" />} {alert.acknowledged ? 'Done' : 'Acknowledge'}</SecondaryButton>
                      {alert.severity !== 'info' && <PrimaryButton>Action</PrimaryButton>}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

function AlertIcon({ severity }: { severity: Alert['severity'] }) {
  return <AlertCircle className={`h-5 w-5 ${severity === 'critical' ? 'text-fleet-red' : severity === 'warning' ? 'text-fleet-amber' : 'text-fleet-blue'}`} />
}
