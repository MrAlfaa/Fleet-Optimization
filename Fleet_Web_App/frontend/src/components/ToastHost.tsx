import { AlertTriangle, CheckCircle2, CircleX, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import type { ToastMessage } from '../utils/toast'

const toneStyles = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-950',
  warning: 'border-amber-200 bg-amber-50 text-amber-950',
  error: 'border-red-200 bg-red-50 text-red-950',
}

const icons = { success: CheckCircle2, warning: AlertTriangle, error: CircleX }

export function ToastHost() {
  const [toast, setToast] = useState<(ToastMessage & { id: number }) | null>(null)

  useEffect(() => {
    let timeout = 0
    const receive = (event: Event) => {
      const detail = (event as CustomEvent<ToastMessage>).detail
      setToast({ ...detail, id: Date.now() })
      window.clearTimeout(timeout)
      timeout = window.setTimeout(() => setToast(null), 4500)
    }
    window.addEventListener('fleetopt:toast', receive)
    return () => { window.removeEventListener('fleetopt:toast', receive); window.clearTimeout(timeout) }
  }, [])

  if (!toast) return null
  const Icon = icons[toast.tone]
  return <div aria-live="polite" className="pointer-events-none fixed bottom-[max(1.5rem,env(safe-area-inset-bottom))] right-4 z-[80] w-[min(390px,calc(100vw-2rem))]" role="status">
    <div className={`pointer-events-auto flex items-start gap-3 rounded-xl border p-4 shadow-2xl motion-safe:animate-[toast-in_220ms_ease-out] ${toneStyles[toast.tone]}`}>
      <Icon className="mt-0.5 h-5 w-5 shrink-0" />
      <div className="min-w-0 flex-1"><div className="font-extrabold">{toast.title}</div>{toast.message && <p className="mt-1 text-sm font-semibold opacity-80">{toast.message}</p>}</div>
      <button aria-label="Dismiss notification" className="rounded-md p-1 transition hover:bg-white/70" onClick={() => setToast(null)} type="button"><X className="h-4 w-4" /></button>
    </div>
  </div>
}
