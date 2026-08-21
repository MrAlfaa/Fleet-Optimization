import { AlertCircle, Bell, CheckCircle2, XCircle } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Card, EmptyState, ErrorState, LoadingState, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import type { Alert } from '../types'
import { useAsyncData } from '../hooks/useAsyncData'
import { fleetService } from '../services/fleetService'

const filters = ['all', 'maintenance', 'route', 'demand', 'driver'] as const

export function AlertsPage() {
  const [filter, setFilter] = useState<(typeof filters)[number]>('all')
  const { data: alerts, error, loading, reload } = useAsyncData(() => fleetService.listAlerts(), [])
  const visible = useMemo(() => {
    const items = alerts ?? []
    return filter === 'all' ? items : items.filter((alert) => alert.category === filter)
  }, [alerts, filter])

  const acknowledge = async (id: string) => {
    await fleetService.resolveAlert(id)
    await reload()
  }

  const dismiss = async (id: string) => {
    await fleetService.dismissAlert(id)
    await reload()
  }

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={reload} />

  return (
    <div>
      <PageHeader
        description="Real-time system anomalies requiring attention."
        title="Alerts Center"
      />
      <div className="mb-4 flex flex-wrap gap-2">
        {filters.map((item) => (
          <button className={`rounded-lg px-4 py-2 text-sm font-semibold capitalize transition ${filter === item ? 'bg-fleet-blue text-white shadow-soft' : 'bg-white text-fleet-muted ring-1 ring-fleet-line hover:bg-slate-50'}`} key={item} onClick={() => setFilter(item)} type="button">
            {item === 'all' ? 'All Filters' : item}
          </button>
        ))}
      </div>
      {visible.length === 0 ? (
        <EmptyState title="No alerts found" description="There are no backend alerts for this filter." />
      ) : (
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
                    <div className="grid gap-3 py-4 md:grid-cols-[72px_minmax(140px,220px)_minmax(0,1fr)_auto] md:items-center md:gap-4" key={alert.id}>
                      <div className="flex items-center gap-2 text-sm font-semibold text-fleet-ink">
                        <AlertIcon severity={alert.severity} />
                        <span className="leading-tight">{alert.time}</span>
                      </div>
                      <div className="min-w-0">
                        <StatusBadge tone="slate"><span className="block max-w-[190px] truncate" title={alert.vehicle}>{alert.vehicle}</span></StatusBadge>
                      </div>
                      <div className="min-w-0">
                        <div className="break-words text-sm font-semibold text-fleet-ink">{alert.title}</div>
                        <p className="mt-1 break-words text-sm font-normal leading-5 text-fleet-muted">{alert.description}</p>
                      </div>
                      <div className="flex flex-wrap gap-2 md:flex-nowrap md:justify-end">
                        <SecondaryButton disabled={alert.acknowledged} onClick={() => acknowledge(alert.id)}>{alert.acknowledged ? <CheckCircle2 className="h-4 w-4" /> : <Bell className="h-4 w-4" />} {alert.acknowledged ? 'Done' : 'Acknowledge'}</SecondaryButton>
                        {alert.severity !== 'info' && <PrimaryButton onClick={() => dismiss(alert.id)}><XCircle className="h-4 w-4" /> Dismiss</PrimaryButton>}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}

function AlertIcon({ severity }: { severity: Alert['severity'] }) {
  return <AlertCircle className={`h-4 w-4 shrink-0 ${severity === 'critical' ? 'text-fleet-red' : severity === 'warning' ? 'text-fleet-amber' : 'text-fleet-blue'}`} />
}
