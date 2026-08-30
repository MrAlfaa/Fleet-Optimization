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
import { ParcelConsolidationPage } from './pages/ParcelConsolidationPage'
import { LoadPlansPage } from './pages/LoadPlansPage'
import { LoadedVehiclesPage } from './pages/LoadedVehiclesPage'
import { VehicleTypesPage } from './pages/VehicleTypesPage'
import { MaintenancePage } from './pages/MaintenancePage'
import { MaintenanceWorkOrdersPage } from './pages/MaintenanceWorkOrdersPage'
import { MaintenanceHistoryPage } from './pages/MaintenanceHistoryPage'
import { InspectionQueuePage } from './pages/InspectionQueuePage'
import { InspectionWorkspacePage } from './pages/InspectionWorkspacePage'
import { RepairDecisionPage } from './pages/RepairDecisionPage'
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
import { LicenseGate } from './components/LicenseGate'

function PermissionRoute({ permission, children }: { permission: string; children: React.ReactNode }) {
  return canAccess(authService.getSession(), permission) ? children : <Navigate replace to="/unauthorized" />
}

const workspaceEntries = [
  ['dashboard.view', '/dashboard'], ['vehicles.view', '/vehicles'], ['maintenance.view', '/maintenance'],
  ['predictive.view', '/predictive-risk'], ['readiness.view', '/fleet-readiness'], ['demand.view', '/demand-forecast'],
  ['zones.view', '/zones'], ['deliveries.view', '/deliveries'], ['load_optimization.view', '/parcel-consolidation'], ['routes.view', '/route-planning'],
  ['live_trips.view', '/live-trips'], ['alerts.view', '/alerts'], ['reports.view', '/reports'],
  ['drivers.manage', '/drivers/manage'], ['permissions.manage', '/users/manage'],
] as const

function WorkspaceHome() {
  const user = authService.getSession()
  const destination = workspaceEntries.find(([permission]) => canAccess(user, permission))?.[1]
  return destination ? <Navigate replace to={destination} /> : <Navigate replace to="/unauthorized" />
}

function UnauthorizedPage() {
  return <div className="grid min-h-[55vh] place-items-center px-6 text-center"><div><div className="text-sm font-bold uppercase text-blue-700">Access restricted</div><h2 className="mt-2 text-2xl font-semibold">This workspace is not assigned to your account</h2><p className="mt-2 text-sm text-slate-500">Contact an administrator if your operational responsibilities have changed.</p></div></div>
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
    <LicenseGate>
      <BrowserRouter>
        <Routes>
        <Route element={<AuthPage mode="login" />} path="/login" />
        <Route element={<Navigate replace to="/login" />} path="/register" />
        <Route element={<RequireAuth />}>
          <Route element={<WorkspaceHome />} index />
          <Route element={<PermissionRoute permission="dashboard.view"><DashboardPage /></PermissionRoute>} path="/dashboard" />
          <Route element={<PermissionRoute permission="vehicles.view"><VehiclesPage /></PermissionRoute>} path="/vehicles" />
          <Route element={<PermissionRoute permission="vehicles.view"><VehicleDetailPage /></PermissionRoute>} path="/vehicles/:vehicleId" />
          <Route element={<PermissionRoute permission="maintenance.view"><MaintenancePage /></PermissionRoute>} path="/maintenance" />
          <Route element={<PermissionRoute permission="maintenance.work_orders.view"><MaintenanceWorkOrdersPage /></PermissionRoute>} path="/maintenance/work-orders" />
          <Route element={<PermissionRoute permission="maintenance.history.view"><MaintenanceHistoryPage /></PermissionRoute>} path="/maintenance/history" />
          <Route element={<PermissionRoute permission="maintenance.inspections.view"><InspectionQueuePage /></PermissionRoute>} path="/maintenance/inspections" />
          <Route element={<PermissionRoute permission="maintenance.inspections.view"><InspectionWorkspacePage /></PermissionRoute>} path="/maintenance/inspections/:inspectionId" />
          <Route element={<PermissionRoute permission="maintenance.inspections.view"><RepairDecisionPage /></PermissionRoute>} path="/maintenance/inspections/:inspectionId/decision" />
          <Route element={<PermissionRoute permission="maintenance.view"><VehicleMaintenancePage /></PermissionRoute>} path="/maintenance/vehicle/:vehicleId" />
          <Route element={<PermissionRoute permission="predictive.view"><PredictiveRiskPage /></PermissionRoute>} path="/predictive-risk" />
          <Route element={<PermissionRoute permission="readiness.view"><FleetReadinessPage /></PermissionRoute>} path="/fleet-readiness" />
          <Route element={<PermissionRoute permission="demand.view"><DemandForecastPage /></PermissionRoute>} path="/demand-forecast" />
          <Route element={<PermissionRoute permission="zones.view"><ZonesPage /></PermissionRoute>} path="/zones" />
          <Route element={<PermissionRoute permission="deliveries.view"><DeliveriesPage /></PermissionRoute>} path="/deliveries" />
          <Route element={<PermissionRoute permission="load_optimization.view"><ParcelConsolidationPage /></PermissionRoute>} path="/parcel-consolidation" />
          <Route element={<Navigate replace to="/route-planning" />} path="/load-optimization" />
          <Route element={<PermissionRoute permission="load_optimization.view"><LoadPlansPage /></PermissionRoute>} path="/load-plans/:planId?" />
          <Route element={<PermissionRoute permission="load_optimization.view"><LoadedVehiclesPage /></PermissionRoute>} path="/loaded-vehicles" />
          <Route element={<PermissionRoute permission="load_optimization.view"><VehicleTypesPage /></PermissionRoute>} path="/vehicle-types" />
          <Route element={<PermissionRoute permission="routes.view"><RoutePlanningPage /></PermissionRoute>} path="/route-planning" />
          <Route element={<PermissionRoute permission="live_trips.view"><LiveTripsPage /></PermissionRoute>} path="/live-trips" />
          <Route element={<PermissionRoute permission="alerts.view"><AlertsPage /></PermissionRoute>} path="/alerts" />
          <Route element={<PermissionRoute permission="reports.view"><ReportsPage /></PermissionRoute>} path="/reports" />
          <Route element={<PermissionRoute permission="drivers.manage"><DriverManagementPage /></PermissionRoute>} path="/drivers/manage" />
          <Route element={<PermissionRoute permission="permissions.manage"><UserManagementPage /></PermissionRoute>} path="/users/manage" />
          <Route element={<UnauthorizedPage />} path="/unauthorized" />
        </Route>
        <Route element={<Navigate replace to="/dashboard" />} path="*" />
        </Routes>
      </BrowserRouter>
    </LicenseGate>
  )
}

export default App
