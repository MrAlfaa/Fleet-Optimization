import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { AuthPage } from './components/AuthLayout'
import { AppShell } from './components/Shell'
import { authService } from './services/authService'
import { AlertsPage } from './pages/AlertsPage'
import { DashboardPage } from './pages/DashboardPage'
import { DeliveriesPage } from './pages/DeliveriesPage'
import { DemandForecastPage } from './pages/DemandForecastPage'
import { LiveTripsPage } from './pages/LiveTripsPage'
import { MaintenancePage } from './pages/MaintenancePage'
import { PredictiveRiskPage } from './pages/PredictiveRiskPage'
import { ReportsPage } from './pages/ReportsPage'
import { RoutePlanningPage } from './pages/RoutePlanningPage'
import { VehicleDetailPage } from './pages/VehicleDetailPage'
import { VehicleMaintenancePage } from './pages/VehicleMaintenancePage'
import { VehiclesPage } from './pages/VehiclesPage'
import { ZonesPage } from './pages/ZonesPage'
import { FleetReadinessPage } from './pages/FleetReadinessPage'
import { DriverManagementPage } from './pages/DriverManagementPage'
import { UserManagementPage } from './pages/UserManagementPage'
import { canAccess } from './utils/permissions'

function PermissionRoute({ permission, children }: { permission: string; children: React.ReactNode }) {
  return canAccess(authService.getSession(), permission) ? children : <Navigate replace to="/dashboard" />
}

function RequireAuth() {
  const [hasInitialSession] = useState(() => Boolean(authService.getSession()))
  const [checking, setChecking] = useState(hasInitialSession)
  const [authenticated, setAuthenticated] = useState(hasInitialSession)

  useEffect(() => {
    let mounted = true
    if (!hasInitialSession) return

    authService
      .restoreSession()
      .then((user) => {
        if (mounted) setAuthenticated(Boolean(user))
      })
      .catch(() => {
        authService.logout()
        if (mounted) setAuthenticated(false)
      })
      .finally(() => {
        if (mounted) setChecking(false)
      })

    return () => {
      mounted = false
    }
  }, [hasInitialSession])

  if (checking) {
    return <WorkspaceLoader />
  }

  return authenticated ? <AppShell /> : <Navigate replace to="/login" />
}

function WorkspaceLoader() {
  return <div className="grid min-h-screen place-items-center bg-[#07111f] px-6 text-white" role="status" aria-live="polite">
    <div className="text-center">
      <div className="relative mx-auto mb-7 h-20 w-20">
        <span className="absolute inset-0 animate-spin rounded-full border border-blue-400/15 border-t-blue-400" />
        <span className="absolute inset-3 animate-[spin_1.5s_linear_infinite_reverse] rounded-full border border-emerald-400/15 border-b-emerald-400" />
        <span className="absolute inset-[30px] animate-pulse rounded-full bg-blue-400 shadow-[0_0_24px_rgba(96,165,250,0.7)]" />
      </div>
      <div className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-300">FleetOpt secure session</div>
      <h2 className="mt-3 text-xl font-semibold">Validating workspace permissions</h2>
      <p className="mt-2 text-sm text-slate-500">Synchronizing your authorized operational modules.</p>
    </div>
  </div>
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AuthPage mode="login" />} path="/login" />
        <Route element={<Navigate replace to="/login" />} path="/register" />
        <Route element={<RequireAuth />}>
          <Route element={<Navigate replace to="/dashboard" />} index />
          <Route element={<PermissionRoute permission="dashboard.view"><DashboardPage /></PermissionRoute>} path="/dashboard" />
          <Route element={<PermissionRoute permission="vehicles.view"><VehiclesPage /></PermissionRoute>} path="/vehicles" />
          <Route element={<PermissionRoute permission="vehicles.view"><VehicleDetailPage /></PermissionRoute>} path="/vehicles/:vehicleId" />
          <Route element={<PermissionRoute permission="maintenance.view"><MaintenancePage /></PermissionRoute>} path="/maintenance" />
          <Route element={<PermissionRoute permission="maintenance.view"><VehicleMaintenancePage /></PermissionRoute>} path="/maintenance/vehicle/:vehicleId" />
          <Route element={<PermissionRoute permission="predictive.view"><PredictiveRiskPage /></PermissionRoute>} path="/predictive-risk" />
          <Route element={<PermissionRoute permission="readiness.view"><FleetReadinessPage /></PermissionRoute>} path="/fleet-readiness" />
          <Route element={<PermissionRoute permission="demand.view"><DemandForecastPage /></PermissionRoute>} path="/demand-forecast" />
          <Route element={<PermissionRoute permission="demand.view"><ZonesPage /></PermissionRoute>} path="/zones" />
          <Route element={<PermissionRoute permission="deliveries.view"><DeliveriesPage /></PermissionRoute>} path="/deliveries" />
          <Route element={<PermissionRoute permission="routes.view"><RoutePlanningPage /></PermissionRoute>} path="/route-planning" />
          <Route element={<PermissionRoute permission="live_trips.view"><LiveTripsPage /></PermissionRoute>} path="/live-trips" />
          <Route element={<PermissionRoute permission="alerts.view"><AlertsPage /></PermissionRoute>} path="/alerts" />
          <Route element={<PermissionRoute permission="reports.view"><ReportsPage /></PermissionRoute>} path="/reports" />
          <Route element={<PermissionRoute permission="drivers.manage"><DriverManagementPage /></PermissionRoute>} path="/drivers/manage" />
          <Route element={<PermissionRoute permission="users.manage"><UserManagementPage /></PermissionRoute>} path="/users/manage" />
        </Route>
        <Route element={<Navigate replace to="/dashboard" />} path="*" />
      </Routes>
    </BrowserRouter>
  )
}

export default App
