import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { fireEvent } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { AppShell } from './Shell'

vi.mock('../services/authService', () => ({
  authService: {
    getSession: () => ({
      id: 'admin-1',
      name: 'Admin User',
      email: 'admin@fleet.local',
      role: 'admin',
      organization: 'FleetOpt AI',
      permissions: ['dashboard.view', 'alerts.view', 'reports.view', 'users.manage', 'drivers.manage'],
    }),
    logout: vi.fn(),
  },
}))

afterEach(cleanup)

describe('AppShell sidebar', () => {
  it('keeps navigation scrollable while the account action remains outside the scroll region', () => {
    render(<MemoryRouter initialEntries={['/dashboard']}><AppShell /></MemoryRouter>)

    expect(screen.getByRole('navigation')).toHaveClass('min-h-0', 'overflow-y-auto')
    expect(screen.getByRole('button', { name: /Admin User Sign out/i }).parentElement).toHaveClass('shrink-0')
  })

  it('connects header actions to navigation and accessible menus', () => {
    function LocationProbe() {
      return <span data-testid="location">{useLocation().pathname}</span>
    }
    render(<MemoryRouter initialEntries={['/dashboard']}><AppShell /><LocationProbe /></MemoryRouter>)

    fireEvent.click(screen.getByRole('button', { name: 'Help' }))
    expect(screen.getByRole('dialog', { name: 'Help and support' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Settings' }))
    expect(screen.getByRole('dialog', { name: 'Workspace settings' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Profile' }))
    expect(screen.getByRole('dialog', { name: 'Profile menu' })).toHaveTextContent('admin@fleet.local')

    fireEvent.click(screen.getByRole('button', { name: 'Notifications' }))
    expect(screen.getByTestId('location')).toHaveTextContent('/alerts')
  })

  it('opens a command search and disables date filters on unsupported pages', () => {
    render(<MemoryRouter initialEntries={['/dashboard']}><AppShell /></MemoryRouter>)
    fireEvent.focus(screen.getByPlaceholderText('Search vehicles, routes, zones...'))
    expect(screen.getByRole('dialog', { name: 'Global search' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Date Range' })).toBeDisabled()
  })
})
