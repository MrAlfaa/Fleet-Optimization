import { Component, lazy, Suspense, useCallback, useMemo, useState, type ReactNode } from 'react'
import { FleetCapacityFallback } from './FleetCapacityFallback'
import { FleetCapacityLegend } from './FleetCapacityLegend'
import { deriveReadinessCapacity, type ReadinessCapacityInput } from './readinessCapacity'

const FleetCapacityScene = lazy(() => import('./FleetCapacityScene'))

interface FleetCapacityVisualizationProps {
  readiness: ReadinessCapacityInput
  className?: string
}

interface SceneErrorBoundaryProps {
  children: ReactNode
  onError: () => void
}

interface SceneErrorBoundaryState {
  failed: boolean
}

class SceneErrorBoundary extends Component<SceneErrorBoundaryProps, SceneErrorBoundaryState> {
  state: SceneErrorBoundaryState = { failed: false }

  static getDerivedStateFromError(): SceneErrorBoundaryState {
    return { failed: true }
  }

  componentDidCatch() {
    this.props.onError()
  }

  render() {
    return this.state.failed ? null : this.props.children
  }
}

function CapacitySceneLoading() {
  return (
    <div
      aria-hidden="true"
      className="absolute inset-0 animate-pulse bg-slate-100 motion-reduce:animate-none"
      data-testid="capacity-scene-loading"
    />
  )
}

export function FleetCapacityVisualization({ readiness, className = '' }: FleetCapacityVisualizationProps) {
  const capacity = useMemo(() => deriveReadinessCapacity(readiness), [readiness])
  const [sceneUnavailable, setSceneUnavailable] = useState(false)
  const [sceneReady, setSceneReady] = useState(false)
  const showFallback = useCallback(() => setSceneUnavailable(true), [])
  const markSceneReady = useCallback(() => setSceneReady(true), [])

  const availabilitySummary = `${capacity.eligible} of ${capacity.required} required vehicles are available for dispatch.`
  const gapSummary = capacity.gap > 0
    ? `Capacity shortage: ${capacity.gap} vehicles.`
    : capacity.spare > 0
      ? `Available reserve: ${capacity.spare} vehicles.`
      : 'Forecast capacity is fully covered.'

  return (
    <section
      aria-label="Dispatch capacity deck"
      className={`min-w-0 border-y border-slate-200 bg-white py-5 ${className}`}
      role="region"
    >
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase text-slate-500">Dispatch capacity deck</p>
          <h2 className="mt-1 text-lg font-bold text-slate-950">{availabilitySummary}</h2>
          <p className={`mt-1 text-sm font-semibold ${capacity.gap > 0 ? 'text-red-700' : 'text-emerald-700'}`}>
            {gapSummary}
          </p>
        </div>
        <div className="rounded-md bg-slate-100 px-3 py-2 text-right">
          <span className="block text-xs font-semibold text-slate-500">Demand coverage</span>
          <span className="text-xl font-bold text-slate-950">{capacity.utilizationPercent}%</span>
        </div>
      </div>

      <div className="relative mt-4 h-[240px] overflow-hidden bg-slate-50 md:h-[320px]">
        {sceneUnavailable ? (
          <FleetCapacityFallback capacity={capacity} />
        ) : (
          <SceneErrorBoundary onError={showFallback}>
            {!sceneReady && <CapacitySceneLoading />}
            <Suspense fallback={null}>
              <FleetCapacityScene
                capacity={capacity}
                onReady={markSceneReady}
                onUnavailable={showFallback}
              />
            </Suspense>
          </SceneErrorBoundary>
        )}
      </div>

      <div className="mt-4">
        <FleetCapacityLegend capacity={capacity} />
      </div>
    </section>
  )
}
