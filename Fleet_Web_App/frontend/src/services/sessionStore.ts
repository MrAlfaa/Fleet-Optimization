import type { User } from '../types'

export const SESSION_KEY = 'fleetopt.session.v1'

export interface StoredSession {
  accessToken: string
  tokenType: string
  user: User
}

export function getStoredSession(): StoredSession | null {
  const raw = localStorage.getItem(SESSION_KEY)
  if (!raw) return null

  try {
    const parsed = JSON.parse(raw) as Partial<StoredSession>
    if (!parsed.accessToken || !parsed.user) {
      localStorage.removeItem(SESSION_KEY)
      return null
    }
    return {
      accessToken: parsed.accessToken,
      tokenType: parsed.tokenType || 'bearer',
      user: parsed.user,
    }
  } catch {
    localStorage.removeItem(SESSION_KEY)
    return null
  }
}

export function saveStoredSession(session: StoredSession): StoredSession {
  localStorage.setItem(SESSION_KEY, JSON.stringify(session))
  return session
}

export function clearStoredSession() {
  localStorage.removeItem(SESSION_KEY)
}

export function getAccessToken(): string | null {
  return getStoredSession()?.accessToken ?? null
}
