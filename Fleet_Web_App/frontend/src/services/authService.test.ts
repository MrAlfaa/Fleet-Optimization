import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authService } from './authService'

const tokenResponse = {
  success: true,
  message: 'Login successful',
  data: {
    access_token: 'test-token',
    token_type: 'bearer',
    user: {
      id: 'usr-001',
      full_name: 'Route Planner',
      email: 'route.planner@fleet.local',
      role: 'route_planner',
    },
  },
}

describe('authService', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('stores a backend session after login', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(tokenResponse), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })))

    const user = await authService.login({
      email: 'route.planner@fleet.local',
      password: 'fleetopt2026',
    })

    expect(user.role).toBe('route_planner')
    expect(authService.getSession()?.email).toBe('route.planner@fleet.local')
  })

  it('clears the local session on logout', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(tokenResponse), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })))

    await authService.login({ email: 'route.planner@fleet.local', password: 'fleetopt2026' })
    authService.logout()

    expect(authService.getSession()).toBeNull()
  })
})
