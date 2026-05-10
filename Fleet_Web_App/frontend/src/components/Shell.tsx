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
  ShieldAlert,
  Truck,
  UserCircle,
  Wrench,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useMemo, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { Brand } from './Brand'
import { authService } from '../services/authService'

interface NavItem {
  label: string
  to: string
  icon: LucideIcon
}

const navItems: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard },
  { label: 'Vehicles', to: '/vehicles', icon: Truck },
  { label: 'Maintenance', to: '/maintenance', icon: Wrench },
  { label: 'Predictive Risk', to: '/predictive-risk', icon: ShieldAlert },
  { label: 'Demand Forecast', to: '/demand-forecast', icon: BarChart3 },
  { label: 'Zones', to: '/zones', icon: Map },
  { label: 'Deliveries', to: '/deliveries', icon: Boxes },
  { label: 'Route Planning', to: '/route-planning', icon: MapPinned },
  { label: 'Live Trips', to: '/live-trips', icon: RadioTower },
  { label: 'Alerts', to: '/alerts', icon: Bell },
  { label: 'Reports', to: '/reports', icon: PackageCheck },
  { label: 'Admin', to: '/reports', icon: Settings },
]

const routeTitles: Record<string, string> = {
  '/dashboard': 'Dashboard Overview',
  '/vehicles': 'Vehicle Registry',
  '/maintenance': 'Maintenance History',
  '/predictive-risk': 'Predictive Risk Dashboard',
  '/demand-forecast': 'Demand Forecast Dashboard',
  '/zones': 'Zone Demand Heatmap',
  '/deliveries': 'Delivery Management',
  '/route-planning': 'Dispatch Configuration',
  '/live-trips': 'Active Deployments',
  '/alerts': 'Alerts Center',
  '/reports': 'Reports and Model Status',
}

export function AppShell() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const user = authService.getSession()
  const title = useMemo(() => {
    if (location.pathname.startsWith('/vehicles/')) return 'Vehicle Detail & Health'
    return routeTitles[location.pathname] ?? 'FleetOpt AI'
  }, [location.pathname])

  const logout = () => {
    authService.logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-fleet-bg text-fleet-ink">
      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-30 flex flex-col bg-gradient-to-b from-[#173b8f] via-[#1f4697] to-[#102a68] px-3 py-5 text-white shadow-2xl transition-all duration-300',
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

        <nav className="flex flex-1 flex-col gap-1.5">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                className={({ isActive }) =>
                  clsx(
                    'group flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold text-blue-100/85 transition',
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

        <div className={clsx('rounded-2xl bg-white/10 p-3 ring-1 ring-white/10', collapsed && 'p-2')}>
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
                <div className="text-sm font-bold">{user?.name ?? 'John Doe'}</div>
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

      <div className={clsx('transition-all duration-300', collapsed ? 'lg:pl-[78px]' : 'lg:pl-[268px]')}>
        <header className="sticky top-0 z-10 border-b border-fleet-line/80 bg-white/86 px-4 py-3 backdrop-blur-xl">
          <div className="flex items-center gap-4">
            <button
              className="rounded-lg border border-fleet-line p-2 text-fleet-muted lg:hidden"
              onClick={() => setMobileOpen(true)}
              type="button"
            >
              <LayoutDashboard className="h-5 w-5" />
            </button>
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold text-fleet-muted">FleetOpt AI</div>
              <h1 className="truncate text-xl font-extrabold tracking-tight text-fleet-ink">{title}</h1>
            </div>
            <div className="hidden min-w-[280px] items-center gap-2 rounded-xl border border-fleet-line bg-slate-50 px-3 py-2 text-sm text-fleet-muted shadow-sm md:flex">
              <Search className="h-4 w-4" />
              <input className="w-full bg-transparent outline-none" placeholder="Search vehicles, routes, zones..." />
            </div>
            <button className="hidden items-center gap-2 rounded-xl border border-fleet-line bg-white px-3 py-2 text-sm font-semibold text-fleet-muted shadow-sm md:flex" type="button">
              <CalendarDays className="h-4 w-4" />
              Date Range
            </button>
            <div className="flex items-center gap-1.5 text-fleet-muted">
              <IconButton icon={Bell} label="Notifications" active />
              <IconButton icon={HelpCircle} label="Help" />
              <IconButton icon={Settings} label="Settings" />
              <IconButton icon={UserCircle} label="Profile" />
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1680px] px-4 py-6 lg:px-7">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

function IconButton({ icon: Icon, label, active = false }: { icon: LucideIcon; label: string; active?: boolean }) {
  return (
    <button
      aria-label={label}
      className="relative rounded-xl p-2 text-fleet-muted transition hover:bg-blue-50 hover:text-fleet-blue"
      type="button"
    >
      <Icon className="h-5 w-5" />
      {active && <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-fleet-red ring-2 ring-white" />}
    </button>
  )
}
