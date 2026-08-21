import type { User } from '../types'

export interface PermissionEntry {
  permission: string
}

export const canAccess = (user: User | null, permission: string): boolean => {
  return Boolean(user?.permissions?.includes(permission))
}

export const visibleNavigation = <T extends PermissionEntry>(entries: T[], user: User | null): T[] => {
  return entries.filter((entry) => canAccess(user, entry.permission))
}
