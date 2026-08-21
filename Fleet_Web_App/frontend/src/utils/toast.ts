export type ToastTone = 'success' | 'warning' | 'error'

export interface ToastMessage {
  title: string
  message?: string
  tone: ToastTone
}

export function showToast(detail: ToastMessage) {
  window.dispatchEvent(new CustomEvent<ToastMessage>('fleetopt:toast', { detail }))
}
