import { describe, expect, it, beforeEach } from 'vitest'
import { authService } from './authService'

describe('authService', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('stores a local session after login', async () => {
    const user = await authService.login({
      email: 'planner@fleetopt.ai',
      password: 'fleetopt2026',
      role: 'planner',
      organization: 'FleetOpt AI Research Lab',
    })

    expect(user.role).toBe('planner')
    expect(authService.getSession()?.email).toBe('planner@fleetopt.ai')
  })

  it('clears the local session on logout', async () => {
    await authService.login({ email: 'manager@fleetopt.ai', password: 'fleetopt2026' })
    authService.logout()

    expect(authService.getSession()).toBeNull()
  })
})
