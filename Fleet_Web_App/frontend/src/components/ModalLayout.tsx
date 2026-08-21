import type { HTMLAttributes, ReactNode } from 'react'

const join = (...values: Array<string | undefined>) => values.filter(Boolean).join(' ')

export function ModalViewport({ children, className, align = 'center' }: { children: ReactNode; className?: string; align?: 'center' | 'right' }) {
  return <div className={join('fixed inset-0 z-50 flex overflow-hidden bg-slate-950/50 p-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] backdrop-blur-sm max-sm:p-4 max-sm:pb-[max(1rem,env(safe-area-inset-bottom))]', align === 'right' ? 'justify-end' : 'items-center justify-center', className)} role="presentation">{children}</div>
}

export function ModalPanel({ children, className, ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={join('flex max-h-[calc(100dvh-3rem)] w-full flex-col overflow-hidden rounded-xl bg-white shadow-2xl max-sm:max-h-[calc(100dvh-2rem)]', className)} data-testid="modal-panel" {...props}>{children}</section>
}

export function ModalHeader({ children, className }: { children: ReactNode; className?: string }) {
  return <header className={join('shrink-0 border-b border-slate-200 px-5 py-4 sm:px-6 sm:py-5', className)}>{children}</header>
}

export function ModalBody({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={join('min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 py-5 sm:px-6', className)}>{children}</div>
}

export function ModalFooter({ children, className }: { children: ReactNode; className?: string }) {
  return <footer className={join('flex shrink-0 flex-col-reverse gap-2 border-t border-slate-200 bg-slate-50 px-5 py-4 pb-[max(1rem,env(safe-area-inset-bottom))] sm:flex-row sm:justify-end sm:px-6', className)}>{children}</footer>
}
