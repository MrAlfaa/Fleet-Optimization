import type { AssessmentEligibility, MaintenanceReviewStatus } from '../../types'

export type AssessmentWorkflowAction =
  | 'complete_profile'
  | 'start_inspection'
  | 'open_inspection_queue'
  | 'import_history'
  | 'view_requirements'
  | 'run_assessment'
  | 'review_assessment'
  | 'open_work_order'
  | 'none'

export interface AssessmentWorkflowPresentation {
  label: string
  description: string
  action: AssessmentWorkflowAction
  runnable: boolean
  tone: 'blue' | 'amber' | 'green' | 'red' | 'slate'
}

export function assessmentWorkflowPresentation(
  eligibility: AssessmentEligibility,
  reviewStatus: MaintenanceReviewStatus | null,
  commissioningPending = false,
): AssessmentWorkflowPresentation {
  if (reviewStatus === 'pending') {
    return { label: 'Review Assessment', description: 'An engineering decision is required before dispatch.', action: 'review_assessment', runnable: false, tone: 'amber' }
  }
  if (reviewStatus === 'confirmed') {
    return { label: 'Open Work Order', description: 'Maintenance was confirmed. Complete the linked work before dispatch.', action: 'open_work_order', runnable: false, tone: 'red' }
  }
  if (eligibility.status === 'profile_incomplete') {
    return { label: 'Complete Vehicle Profile', description: 'Required vehicle details must be recorded first.', action: 'complete_profile', runnable: false, tone: 'amber' }
  }
  if (eligibility.status === 'commissioning_required') {
    return commissioningPending
      ? { label: 'Open Inspection Queue', description: 'The initial inspection is waiting to be completed.', action: 'open_inspection_queue', runnable: false, tone: 'amber' }
      : { label: 'Start Initial Inspection', description: 'Commission this vehicle before building its assessment history.', action: 'start_inspection', runnable: false, tone: 'amber' }
  }
  if (eligibility.status === 'building_history' && eligibility.onboardingType === 'existing_fleet') {
    return { label: 'Import Service History', description: 'Add at least one completed historical service record.', action: 'import_history', runnable: false, tone: 'amber' }
  }
  if (eligibility.status === 'building_history') {
    const trips = eligibility.requirements.completedTrips
    const distance = eligibility.requirements.recordedDistanceKm
    return {
      label: `Trips ${trips.current}/${trips.required} · Distance ${formatDistance(distance.current)}/${formatDistance(distance.required)} km`,
      description: 'This new vehicle is still building enough operating history.',
      action: 'view_requirements',
      runnable: false,
      tone: 'blue',
    }
  }
  if (eligibility.status === 'new_assessment_available') {
    return { label: 'Run Updated Assessment', description: 'New mileage, trip, inspection, or service evidence is available.', action: 'run_assessment', runnable: true, tone: 'blue' }
  }
  if (eligibility.status === 'assessment_current') {
    return { label: 'Assessment up to date', description: 'No new operating evidence has been recorded.', action: 'none', runnable: false, tone: 'green' }
  }
  return { label: 'Run Risk Assessment', description: 'Required operating evidence is complete.', action: 'run_assessment', runnable: true, tone: 'blue' }
}

function formatDistance(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1)
}
