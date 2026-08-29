import { CalendarClock, LockKeyhole, RefreshCw } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { licenseService, type LicenseStatus } from '../services/licenseService'

export function LicenseGate({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<LicenseStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const requestStatus = useCallback(async () => {
    try {
      setStatus(await licenseService.getStatus())
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to contact the FleetOpt backend.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let mounted = true
    licenseService
      .getStatus()
      .then((nextStatus) => {
        if (mounted) setStatus(nextStatus)
      })
      .catch((requestError: unknown) => {
        if (mounted) setError(requestError instanceof Error ? requestError.message : 'Unable to contact the FleetOpt backend.')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  const retryValidation = useCallback(() => {
    setLoading(true)
    setError(null)
    void requestStatus()
  }, [requestStatus])

  if (loading) {
    return <AccessState title="Checking research access" detail="Validating the local deployment configuration." />
  }

  if (error) {
    return <AccessState title="Backend connection unavailable" detail={error} action={retryValidation} />
  }

  if (status?.blocked) {
    const title = status.status === 'expired' ? 'Research access period ended' : 'Deployment configuration required'
    return (
      <AccessState
        title={title}
        detail={status.supportMessage}
        customerName={status.customerName}
        expiresAt={status.expiresAt}
        action={retryValidation}
      />
    )
  }

  return children
}

function AccessState({
  title,
  detail,
  customerName,
  expiresAt,
  action,
}: {
  title: string
  detail: string
  customerName?: string
  expiresAt?: string | null
  action?: () => void | Promise<void>
}) {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-50 px-6 py-12 text-slate-950">
      <section className="w-full max-w-lg rounded-lg border border-slate-200 bg-white p-8 shadow-sm" aria-live="polite">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
          <LockKeyhole aria-hidden="true" size={24} />
        </div>
        <p className="mt-6 text-xs font-bold uppercase text-blue-700">FleetOpt research deployment</p>
        <h1 className="mt-2 text-2xl font-semibold">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">{detail}</p>
        {(customerName || expiresAt) && (
          <dl className="mt-6 border-y border-slate-200 py-4 text-sm">
            {customerName && <div className="flex justify-between gap-4"><dt className="text-slate-500">Deployment</dt><dd className="font-medium text-right">{customerName}</dd></div>}
            {expiresAt && <div className="mt-3 flex justify-between gap-4"><dt className="flex items-center gap-2 text-slate-500"><CalendarClock size={16} />Access end</dt><dd className="font-medium text-right">{formatExpiry(expiresAt)}</dd></div>}
          </dl>
        )}
        {action && (
          <button className="mt-6 inline-flex h-10 items-center gap-2 rounded-md bg-blue-700 px-4 text-sm font-semibold text-white hover:bg-blue-800" onClick={() => void action()} type="button">
            <RefreshCw size={16} /> Retry validation
          </button>
        )}
      </section>
    </main>
  )
}

function formatExpiry(value: string) {
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat('en-LK', { dateStyle: 'medium', timeStyle: 'short' }).format(date)
}
