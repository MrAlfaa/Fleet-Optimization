import {
  BarChart3,
  Bell,
  Boxes,
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  LayoutDashboard,
  Map,
  MapPinned,
  PackageCheck,
  RadioTower,
  Search,
  Settings,
  LogOut,
  ShieldAlert,
  ShieldCheck,
  Truck,
  UserCircle,
  Users,
  Wrench,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { Brand } from './Brand'
import { authService } from '../services/authService'
import { canAccess, visibleNavigation } from '../utils/permissions'
import { searchService, type SearchResult } from '../services/searchService'
import { ToastHost } from './ToastHost'

interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  permission: string
}

const navItems: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard, permission: 'dashboard.view' },
  { label: 'Vehicles', to: '/vehicles', icon: Truck, permission: 'vehicles.view' },
  { label: 'Maintenance', to: '/maintenance', icon: Wrench, permission: 'maintenance.view' },
  { label: 'Risk Assessments', to: '/predictive-risk', icon: ShieldAlert, permission: 'predictive.view' },
  { label: 'Fleet Readiness', to: '/fleet-readiness', icon: ShieldCheck, permission: 'readiness.view' },
  { label: 'Demand Forecast', to: '/demand-forecast', icon: BarChart3, permission: 'demand.view' },
  { label: 'Zones', to: '/zones', icon: Map, permission: 'zones.view' },
  { label: 'Parcel Gallery', to: '/deliveries', icon: Boxes, permission: 'deliveries.view' },
  { label: 'Parcel Consolidation', to: '/parcel-consolidation', icon: Boxes, permission: 'load_optimization.view' },
  { label: 'Route Optimization & Load Balancing', to: '/route-planning', icon: MapPinned, permission: 'routes.view' },
  { label: 'Live Trips', to: '/live-trips', icon: RadioTower, permission: 'live_trips.view' },
  { label: 'Alerts', to: '/alerts', icon: Bell, permission: 'alerts.view' },
  { label: 'Reports', to: '/reports', icon: PackageCheck, permission: 'reports.view' },
]

const routeTitles: Record<string, string> = {
  '/dashboard': 'Dashboard Overview',
  '/vehicles': 'Vehicle Registry',
  '/maintenance': 'Maintenance Command Center',
  '/maintenance/work-orders': 'Maintenance Work Orders',
  '/maintenance/history': 'Maintenance History',
  '/maintenance/inspections': 'Inspection Queue',
  '/predictive-risk': 'Vehicle Risk Assessments',
  '/fleet-readiness': 'Fleet Readiness',
  '/demand-forecast': 'Demand Forecast Dashboard',
  '/zones': 'Zone Demand Heatmap',
  '/deliveries': 'Parcel Gallery',
  '/parcel-consolidation': 'Parcel Consolidation - HDBSCAN Clustering',
  '/load-plans': 'Load Plans',
  '/loaded-vehicles': 'Loaded Vehicles - Fleet Handoff',
  '/vehicle-types': 'Vehicle Types - Optimizer Catalog',
  '/route-planning': 'Route Optimization and Load Balancing',
  '/live-trips': 'Active Deployments',
  '/alerts': 'Alerts Center',
  '/reports': 'Reports',
  '/drivers/manage': 'Driver Management',
  '/users/manage': 'User Access Control',
}

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [headerMenu, setHeaderMenu] = useState<'help' | 'settings' | 'profile' | null>(null)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [dateOpen, setDateOpen] = useState(false)
  const [dateRange, setDateRange] = useState(() => ({ start: localStorage.getItem('fleetopt-date-start') || '', end: localStorage.getItem('fleetopt-date-end') || '' }))
  const location = useLocation()
  const navigate = useNavigate()
  const user = authService.getSession()
  const navigationItems = useMemo(() => visibleNavigation([
    ...navItems,
    { label: 'Driver Management', to: '/drivers/manage', icon: Users, permission: 'drivers.manage' },
    { label: 'User Access', to: '/users/manage', icon: UserCircle, permission: 'permissions.manage' },
  ], user), [user])
  const pageResults = useMemo<SearchResult[]>(() => {
    const query = searchQuery.trim().toLowerCase()
    if (query.length < 2) return []
    return navigationItems
      .filter((item) => item.label.toLowerCase().includes(query))
      .map((item) => ({ id: item.to, type: 'page', title: item.label, subtitle: 'Application page', path: item.to }))
  }, [navigationItems, searchQuery])
  const combinedSearchResults = useMemo(() => {
    const seen = new Set(pageResults.map((item) => item.path))
    return [...pageResults, ...searchResults.filter((item) => !seen.has(item.path))]
  }, [pageResults, searchResults])
  const dateSupported = ['/demand-forecast', '/reports'].includes(location.pathname)
  const title = useMemo(() => {
    if (location.pathname.startsWith('/vehicles/')) return 'Vehicle Workspace'
    if (location.pathname.startsWith('/load-plans/')) return 'Load Plans'
    if (/^\/maintenance\/inspections\/[^/]+\/decision$/.test(location.pathname)) return 'Repair Decision'
    if (/^\/maintenance\/inspections\/[^/]+$/.test(location.pathname)) return 'Mechanic Inspection Workspace'
    return routeTitles[location.pathname] ?? 'FleetOpt AI'
  }, [location.pathname])

  const logout = () => {
    authService.logout()
    navigate('/login')
  }

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (searchQuery.trim().length < 2) setSearchResults([])
      else searchService.search(searchQuery).then(setSearchResults).catch(() => setSearchResults([]))
    }, 250)
    return () => window.clearTimeout(timer)
  }, [searchQuery])

  const applyDateRange = () => {
    if (dateRange.start && dateRange.end && dateRange.start > dateRange.end) return
    localStorage.setItem('fleetopt-date-start', dateRange.start)
    localStorage.setItem('fleetopt-date-end', dateRange.end)
    window.dispatchEvent(new CustomEvent('fleetopt-date-range', { detail: dateRange }))
    setDateOpen(false)
  }

  return (
    <div className="min-h-screen max-w-full overflow-x-clip bg-fleet-bg text-fleet-ink">
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-30 flex flex-col overflow-hidden bg-gradient-to-b from-[#173b8f] via-[#1f4697] to-[#102a68] px-3 py-5 text-white shadow-2xl transition-all duration-300',
          collapsed ? 'w-[78px]' : 'w-[268px]',
          mobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
        )}
      >
        <div className="mb-8 flex items-center justify-between px-1">
          <Brand compact={collapsed} />
          <button
            aria-label="Collapse sidebar"
            className="hidden rounded-lg p-2 text-blue-100 transition hover:bg-white/10 lg:block"
            onClick={() => setCollapsed((value) => !value)}
            type="button"
          >
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
        </div>

        <nav className="sidebar-scroll flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto pr-1">
          {navigationItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                className={({ isActive }) =>
                  clsx(
                    'group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-blue-100/85 transition',
                    'hover:bg-white/10 hover:text-white',
                    isActive && 'bg-white/14 text-white ring-1 ring-white/10',
                    collapsed && 'justify-center px-2',
                  )
                }
                key={item.label}
                onClick={() => setMobileOpen(false)}
                to={item.to}
              >
                <Icon className="h-5 w-5 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            )
          })}
        </nav>

        <div className={clsx('mt-3 shrink-0 rounded-2xl bg-white/10 p-3 ring-1 ring-white/10', collapsed && 'p-2')}>
          <button
            className={clsx('flex w-full items-center gap-3 text-left', collapsed && 'justify-center')}
            onClick={logout}
            type="button"
          >
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white text-sm font-bold text-fleet-navy">
              {user?.name.slice(0, 2).toUpperCase() ?? 'JD'}
            </div>
            {!collapsed && (
              <div>
                <div className="text-sm font-semibold">{user?.name ?? 'John Doe'}</div>
                <div className="text-xs text-blue-100/75">Sign out</div>
              </div>
            )}
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <button
          aria-label="Close mobile navigation"
          className="fixed inset-0 z-20 bg-slate-950/40 lg:hidden"
          onClick={() => setMobileOpen(false)}
          type="button"
        />
      )}

      <div className={clsx('min-w-0 max-w-full transition-all duration-300', collapsed ? 'lg:pl-[78px]' : 'lg:pl-[268px]')}>
        <header className="sticky top-0 z-10 min-w-0 max-w-full overflow-x-clip border-b border-fleet-line/80 bg-white/86 px-3 py-3 backdrop-blur-xl sm:px-4">
          <div className="flex min-w-0 items-center gap-2 sm:gap-4">
            <button
              className="rounded-lg border border-fleet-line p-2 text-fleet-muted lg:hidden"
              onClick={() => setMobileOpen(true)}
              type="button"
            >
              <LayoutDashboard className="h-5 w-5" />
            </button>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-medium text-fleet-muted">FleetOpt AI</div>
              <h1 className="truncate text-lg font-semibold tracking-normal text-fleet-ink">{title}</h1>
            </div>
            <div className="relative hidden min-w-0 max-w-[280px] flex-1 items-center gap-2 rounded-xl border border-fleet-line bg-slate-50 px-3 py-2 text-sm text-fleet-muted shadow-sm md:flex xl:max-w-[360px]">
              <Search className="h-4 w-4" />
              <input className="w-full bg-transparent outline-none" onChange={(event) => setSearchQuery(event.target.value)} onFocus={() => setSearchOpen(true)} placeholder="Search vehicles, routes, zones..." value={searchQuery} />
              {searchOpen && <div aria-label="Global search" className="absolute right-0 top-12 z-50 w-[420px] max-w-[calc(100vw-2rem)] rounded-lg border border-fleet-line bg-white p-2 shadow-2xl" role="dialog">
                <div className="flex items-center justify-between px-3 py-2"><span className="text-xs font-semibold uppercase text-fleet-muted">Global search</span><button aria-label="Close search" onClick={() => setSearchOpen(false)} type="button">×</button></div>
                {searchQuery.length < 2 ? <p className="px-3 py-5 text-sm">Type at least two characters.</p> : combinedSearchResults.length === 0 ? <p className="px-3 py-5 text-sm">No matching records yet.</p> : combinedSearchResults.map((result) => <button className="flex w-full items-start justify-between rounded-lg px-3 py-2 text-left hover:bg-slate-50" key={`${result.type}-${result.id}`} onClick={() => { setSearchOpen(false); setSearchQuery(''); navigate(result.path) }} type="button"><span><span className="block font-semibold text-fleet-ink">{result.title}</span><span className="text-xs text-fleet-muted">{result.subtitle}</span></span><span className="rounded bg-slate-100 px-2 py-1 text-[10px] uppercase">{result.type}</span></button>)}
              </div>}
            </div>
            <div className="relative hidden md:block"><button aria-label="Date Range" className="flex items-center gap-2 rounded-xl border border-fleet-line bg-white px-3 py-2 text-sm font-semibold text-fleet-muted shadow-sm disabled:cursor-not-allowed disabled:opacity-45" disabled={!dateSupported} onClick={() => setDateOpen((value) => !value)} title={dateSupported ? 'Filter this analytical page' : 'Date filtering is not supported on this page'} type="button">
              <CalendarDays className="h-4 w-4" />
              Date Range
            </button>{dateOpen && <div className="absolute right-0 top-12 z-50 w-72 rounded-lg border border-fleet-line bg-white p-4 shadow-2xl"><label className="block text-xs font-semibold text-fleet-muted">Start<input className="mt-1 w-full rounded-lg border border-fleet-line p-2" onChange={(event) => setDateRange((value) => ({ ...value, start: event.target.value }))} type="date" value={dateRange.start} /></label><label className="mt-3 block text-xs font-semibold text-fleet-muted">End<input className="mt-1 w-full rounded-lg border border-fleet-line p-2" onChange={(event) => setDateRange((value) => ({ ...value, end: event.target.value }))} type="date" value={dateRange.end} /></label>{dateRange.start && dateRange.end && dateRange.start > dateRange.end && <p className="mt-2 text-xs text-red-600">Start date must be before end date.</p>}<button className="mt-3 w-full rounded-lg bg-fleet-blue px-3 py-2 text-sm font-semibold text-white" onClick={applyDateRange} type="button">Apply range</button></div>}</div>
            <div className="relative flex shrink-0 items-center gap-0.5 text-fleet-muted sm:gap-1.5">
              {canAccess(user, 'alerts.view') && <IconButton icon={Bell} label="Notifications" active onClick={() => navigate('/alerts')} />}
              <span className="hidden sm:inline-flex"><IconButton expanded={headerMenu === 'help'} icon={HelpCircle} label="Help" onClick={() => setHeaderMenu((value) => value === 'help' ? null : 'help')} /></span>
              <span className="hidden lg:inline-flex"><IconButton expanded={headerMenu === 'settings'} icon={Settings} label="Settings" onClick={() => setHeaderMenu((value) => value === 'settings' ? null : 'settings')} /></span>
              <IconButton expanded={headerMenu === 'profile'} icon={UserCircle} label="Profile" onClick={() => setHeaderMenu((value) => value === 'profile' ? null : 'profile')} />
              {headerMenu && <HeaderMenu menu={headerMenu} navigateTo={(path) => { setHeaderMenu(null); navigate(path) }} onLogout={logout} user={user} />}
            </div>
          </div>
        </header>

        <main className="mx-auto min-w-0 w-full max-w-[1680px] overflow-x-clip px-3 pt-5 pb-[max(3rem,env(safe-area-inset-bottom))] sm:px-4 lg:px-7 lg:pt-6 lg:pb-[max(4rem,env(safe-area-inset-bottom))]">
          <Outlet />
        </main>
      </div>
      <ToastHost />
    </div>
  )
}

function IconButton({ icon: Icon, label, active = false, expanded = false, onClick }: { icon: LucideIcon; label: string; active?: boolean; expanded?: boolean; onClick?: () => void }) {
  return (
    <button
      aria-label={label}
      aria-expanded={expanded}
      className="relative rounded-xl p-2 text-fleet-muted transition hover:bg-blue-50 hover:text-fleet-blue"
      onClick={onClick}
      type="button"
    >
      <Icon className="h-5 w-5" />
      {active && <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-fleet-red ring-2 ring-white" />}
    </button>
  )
}

function HeaderMenu({ menu, navigateTo, onLogout, user }: { menu: 'help' | 'settings' | 'profile'; navigateTo: (path: string) => void; onLogout: () => void; user: ReturnType<typeof authService.getSession> }) {
  const title = menu === 'help' ? 'Help and support' : menu === 'settings' ? 'Workspace settings' : 'Profile menu'
  return <div aria-label={title} className="absolute right-0 top-12 z-50 w-72 rounded-lg border border-fleet-line bg-white p-2 text-fleet-ink shadow-xl" role="dialog">
    <div className="border-b border-fleet-line px-3 py-2"><div className="text-sm font-semibold">{title}</div>{menu === 'profile' && <div className="mt-1 truncate text-xs text-fleet-muted">{user?.email}</div>}</div>
    {menu === 'help' && <div className="p-1"><MenuAction label="Open operational reports" onClick={() => navigateTo('/reports')} /><MenuAction label="Review operational alerts" onClick={() => navigateTo('/alerts')} /></div>}
    {menu === 'settings' && <div className="p-1">{canAccess(user, 'permissions.manage') && <MenuAction label="Manage user access" onClick={() => navigateTo('/users/manage')} />}{canAccess(user, 'drivers.manage') && <MenuAction label="Manage driver devices" onClick={() => navigateTo('/drivers/manage')} />}<div className="px-3 py-2 text-xs text-fleet-muted">Access is controlled by your assigned permissions.</div></div>}
    {menu === 'profile' && <div className="p-1"><div className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-fleet-muted">{user?.role.replace('_', ' ')}</div><button className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm font-semibold text-red-700 hover:bg-red-50" onClick={onLogout} type="button"><LogOut className="h-4 w-4" />Sign out</button></div>}
  </div>
}

function MenuAction({ label, onClick }: { label: string; onClick: () => void }) {
  return <button className="flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm font-medium hover:bg-slate-50" onClick={onClick} type="button"><span>{label}</span><ChevronRight className="h-4 w-4 text-fleet-muted" /></button>
}
