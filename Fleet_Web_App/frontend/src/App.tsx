import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
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
import { VehiclesPage } from './pages/VehiclesPage'
import { ZonesPage } from './pages/ZonesPage'

function RequireAuth() {
  return authService.getSession() ? <AppShell /> : <Navigate replace to="/login" />
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AuthPage mode="login" />} path="/login" />
        <Route element={<AuthPage mode="register" />} path="/register" />
        <Route element={<RequireAuth />}>
          <Route element={<Navigate replace to="/dashboard" />} index />
          <Route element={<DashboardPage />} path="/dashboard" />
          <Route element={<VehiclesPage />} path="/vehicles" />
          <Route element={<VehicleDetailPage />} path="/vehicles/:vehicleId" />
          <Route element={<MaintenancePage />} path="/maintenance" />
          <Route element={<PredictiveRiskPage />} path="/predictive-risk" />
          <Route element={<DemandForecastPage />} path="/demand-forecast" />
          <Route element={<ZonesPage />} path="/zones" />
          <Route element={<DeliveriesPage />} path="/deliveries" />
          <Route element={<RoutePlanningPage />} path="/route-planning" />
          <Route element={<LiveTripsPage />} path="/live-trips" />
          <Route element={<AlertsPage />} path="/alerts" />
          <Route element={<ReportsPage />} path="/reports" />
        </Route>
        <Route element={<Navigate replace to="/dashboard" />} path="*" />
      </Routes>
    </BrowserRouter>
  )
}

export default App
