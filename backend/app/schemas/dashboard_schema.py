from pydantic import BaseModel


class FleetDashboardSummary(BaseModel):
    total_vehicles: int
    active_vehicles: int
    under_maintenance: int
    critical_vehicles: int
    active_alerts: int
    upcoming_maintenance: int
    completed_maintenance_this_month: int


class FleetHealthDistribution(BaseModel):
    healthy: int
    warning: int
    critical: int
    unknown: int


class MaintenanceSummary(BaseModel):
    scheduled: int
    in_progress: int
    completed: int
    cancelled: int
    high_priority: int
    critical_priority: int


class AlertSummary(BaseModel):
    active: int
    resolved: int
    dismissed: int
    critical: int
    high: int
    warning: int
    info: int
