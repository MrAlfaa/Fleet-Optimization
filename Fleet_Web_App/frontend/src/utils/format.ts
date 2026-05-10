import clsx from 'clsx'
import type { RiskLevel } from '../types'

export const formatNumber = (value: number) => value.toLocaleString('en-US')

export const riskBadgeClass = (risk: RiskLevel) =>
  clsx(
    'inline-flex items-center rounded-md px-2 py-1 text-xs font-semibold capitalize',
    risk === 'low' && 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
    risk === 'medium' && 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
    risk === 'high' && 'bg-orange-50 text-orange-700 ring-1 ring-orange-200',
    risk === 'critical' && 'bg-red-50 text-red-700 ring-1 ring-red-200',
  )

export const statusDotClass = (risk: RiskLevel) =>
  clsx(
    'h-2 w-2 rounded-full',
    risk === 'low' && 'bg-emerald-500',
    risk === 'medium' && 'bg-amber-500',
    risk === 'high' && 'bg-orange-500',
    risk === 'critical' && 'bg-red-500',
  )
