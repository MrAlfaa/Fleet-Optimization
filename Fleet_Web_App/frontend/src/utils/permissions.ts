import type { User } from '../types'

export interface PermissionEntry {
  permission: string
}

export interface PermissionMetadata {
  key: string
  label: string
  type: 'page' | 'tab' | 'action'
  description: string
  parent?: string
}

export const canAccess = (user: User | null, permission: string): boolean => {
  return Boolean(user && (user.role === 'admin' || user.permissions?.includes(permission)))
}

export const visibleNavigation = <T extends PermissionEntry>(entries: T[], user: User | null): T[] => {
  return entries.filter((entry) => canAccess(user, entry.permission))
}

export const togglePermission = (
  current: string[],
  permission: string,
  enabled: boolean,
  metadata: Record<string, PermissionMetadata>,
): string[] => {
  const next = new Set(current)
  if (enabled) {
    let candidate: string | undefined = permission
    while (candidate) {
      next.add(candidate)
      candidate = metadata[candidate]?.parent
    }
  } else {
    next.delete(permission)
    let changed = true
    while (changed) {
      changed = false
      Object.values(metadata).forEach((item) => {
        if (item.parent && !next.has(item.parent) && next.delete(item.key)) changed = true
      })
    }
  }
  return [...next].sort()
}

export const firstAccessiblePermission = (ordered: string[], assigned: string[]): string | null => {
  return ordered.find((permission) => assigned.includes(permission)) ?? null
}
