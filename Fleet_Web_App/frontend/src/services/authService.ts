import { demoUser } from '../data/mockData'
import type { User, UserRole } from '../types'

const SESSION_KEY = 'fleetopt.session.v1'

interface AuthPayload {
  email: string
  password: string
  role?: UserRole
  organization?: string
}

const persist = (user: User) => {
  localStorage.setItem(SESSION_KEY, JSON.stringify(user))
  return user
}

export const authService = {
  getSession(): User | null {
    const raw = localStorage.getItem(SESSION_KEY)
    if (!raw) return null
    try {
      return JSON.parse(raw) as User
    } catch {
      localStorage.removeItem(SESSION_KEY)
      return null
    }
  },
  login(payload: AuthPayload): Promise<User> {
    const user: User = {
      ...demoUser,
      email: payload.email || demoUser.email,
      role: payload.role ?? demoUser.role,
      organization: payload.organization || demoUser.organization,
    }
    return Promise.resolve(persist(user))
  },
  register(payload: AuthPayload & { name: string }): Promise<User> {
    const user: User = {
      ...demoUser,
      id: `usr-${Date.now()}`,
      name: payload.name,
      email: payload.email,
      role: payload.role ?? 'fleet_manager',
      organization: payload.organization || 'FleetOpt AI Research Lab',
    }
    return Promise.resolve(persist(user))
  },
  logout() {
    localStorage.removeItem(SESSION_KEY)
  },
}
