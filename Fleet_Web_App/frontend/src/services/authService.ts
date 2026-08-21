import type { User, UserRole } from '../types'
import { apiClient } from './apiClient'
import { clearStoredSession, getStoredSession, saveStoredSession } from './sessionStore'

interface AuthPayload {
  email: string
  password: string
}

interface BackendUser {
  id: string
  full_name?: string
  name?: string
  email: string
  role: UserRole
  organization?: string
  permissions?: string[]
}

interface TokenPayload {
  access_token: string
  token_type: string
  user: BackendUser
}

const mapUser = (user: BackendUser): User => {
  return {
    id: user.id,
    name: user.full_name || user.name || 'FleetOpt User',
    email: user.email,
    role: user.role,
    organization: user.organization || 'FleetOpt AI',
    permissions: user.permissions ?? [],
  }
}

const persistToken = (payload: TokenPayload) => {
  const user = mapUser(payload.user)
  saveStoredSession({
    accessToken: payload.access_token,
    tokenType: payload.token_type || 'bearer',
    user,
  })
  return user
}

export const authService = {
  getSession(): User | null {
    return getStoredSession()?.user ?? null
  },
  async restoreSession(): Promise<User | null> {
    if (!getStoredSession()) return null
    const user = await apiClient.get<BackendUser>('/auth/me')
    const session = getStoredSession()
    if (!session) return null
    saveStoredSession({ ...session, user: mapUser(user) })
    return mapUser(user)
  },
  async login(payload: AuthPayload): Promise<User> {
    const data = await apiClient.post<TokenPayload>(
      '/auth/login',
      {
        email: payload.email,
        password: payload.password,
      },
      { skipAuth: true },
    )
    return persistToken(data)
  },
  logout() {
    clearStoredSession()
  },
}
