import type { LoadPlan } from '../loadOptimization/types'
import type { RouteSet } from '../../types'

export function routeSetWorkflow(plan: LoadPlan | null, routeSet: RouteSet | null) {
  const loads = plan?.selected_option?.loads ?? []
  const allVehiclesAssigned = loads.length > 0 && loads.every((load) => Boolean(load.assigned_vehicle_id))
  const allDriversAssigned = Boolean(routeSet?.routes.length) && routeSet!.routes.every((route) => route.driver && route.driver !== 'Unassigned')
  return {
    allVehiclesAssigned,
    allDriversAssigned,
    canGenerateRoutes: plan?.status === 'approved' && allVehiclesAssigned && !routeSet,
    canApproveRoutes: routeSet?.status === 'review_required',
    canAssignDrivers: routeSet?.status === 'approved',
    canDispatch: routeSet?.status === 'approved' && allDriversAssigned,
  }
}
