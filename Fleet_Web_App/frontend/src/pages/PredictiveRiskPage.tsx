import {
  Activity,
  AlertTriangle,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  DatabaseZap,
  Gauge,
  History,
  RefreshCw,
  Search,
  ShieldAlert,
  Wrench,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Card,
  DataTable,
  EmptyState,
  ErrorState,
  LoadingState,
  MetricCard,
  OperationalInfo,
  PageHeader,
  PrimaryButton,
  RiskBadge,
  SecondaryButton,
  StatusBadge,
} from "../components/UI";
import { MaintenanceRecordDialog } from "../components/MaintenanceRecordDialog";
import { ModalBody, ModalFooter, ModalHeader, ModalPanel, ModalViewport } from "../components/ModalLayout";
import { PredictionReviewDialog } from "../components/PredictionReviewDialog";
import { assessmentWorkflowPresentation } from "../features/predictive/assessmentWorkflow";
import { summarizeLatestFleetRisk } from "../features/predictive/maintenanceRisk";
import { useAsyncData } from "../hooks/useAsyncData";
import { fleetService } from "../services/fleetService";
import { authService } from "../services/authService";
import { canAccess } from "../utils/permissions";
import { showToast } from "../utils/toast";
import type { AssessmentEligibility, MaintenancePrediction } from "../types";

export function PredictiveRiskPage() {
  const navigate = useNavigate();
  const currentUser = authService.getSession();
  const canRunAssessment = canAccess(currentUser, "predictive.run");
  const canManageMaintenance = canAccess(currentUser, "maintenance.manage");
  const [query, setQuery] = useState("");
  const [selectedVehicleId, setSelectedVehicleId] = useState("");
  const [busy, setBusy] = useState(false);
  const [eligibilityResult, setEligibilityResult] = useState<{ vehicleId: string; value: AssessmentEligibility | null; error: string } | null>(null);
  const [dialogError, setDialogError] = useState("");
  const [showRequirements, setShowRequirements] = useState(false);
  const [showReview, setShowReview] = useState(false);
  const [showMaintenance, setShowMaintenance] = useState(false);
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [status, predictions, vehicles, reviews] = await Promise.all([
      fleetService.getSensorFreeModelStatus(),
      fleetService.listMaintenancePredictions(),
      fleetService.listVehicles(),
      fleetService.listPredictionReviews(),
    ]);
    return { status, predictions, vehicles, reviews };
  }, []);

  const fleetRisk = useMemo(
    () => summarizeLatestFleetRisk(data?.predictions ?? []),
    [data],
  );
  const latestByVehicle = fleetRisk.latestByVehicle;
  const rows = useMemo(
    () =>
      (data?.vehicles ?? []).filter((vehicle) =>
        `${vehicle.registrationNumber} ${vehicle.vehicleCode} ${vehicle.model}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [data, query],
  );
  const selectedVehicle = (data?.vehicles ?? []).find(
    (vehicle) => vehicle.id === selectedVehicleId,
  );
  const selectedPrediction = selectedVehicle
    ? latestByVehicle.get(selectedVehicle.id)
    : undefined;
  const eligibility = eligibilityResult?.vehicleId === selectedVehicleId
    ? eligibilityResult.value
    : null;
  const eligibilityLoading = Boolean(selectedVehicleId && eligibilityResult?.vehicleId !== selectedVehicleId);
  const eligibilityError = eligibilityResult?.vehicleId === selectedVehicleId ? eligibilityResult.error : "";
  const selectedReview = data?.reviews.find(
    (review) => review.vehicleId === selectedVehicleId && (review.status === "pending" || review.status === "confirmed"),
  ) ?? data?.reviews.find((review) => review.predictionId === selectedPrediction?.id);
  const selectedReviewId = selectedPrediction?.reviewId || selectedReview?.id || "";
  const workflow = eligibility
    ? assessmentWorkflowPresentation(
      eligibility,
      selectedReview?.status ?? selectedPrediction?.reviewStatus ?? null,
      selectedVehicle?.commissioningStatus === "pending",
    )
    : null;

  useEffect(() => {
    if (!selectedVehicleId) return;
    let active = true;
    fleetService.getAssessmentEligibility(selectedVehicleId)
      .then((result) => { if (active) setEligibilityResult({ vehicleId: selectedVehicleId, value: result, error: "" }); })
      .catch((reason) => {
        if (!active) return;
        const message = reason instanceof Error ? reason.message : "Unable to load assessment requirements";
        setEligibilityResult({ vehicleId: selectedVehicleId, value: null, error: message });
        setDialogError(message);
      })
    return () => { active = false; };
  }, [selectedVehicleId, data?.predictions.length, data?.reviews.length]);

  const recalculate = async () => {
    if (!selectedVehicle || !workflow?.runnable) {
      if (selectedVehicle) setShowRequirements(true);
      return;
    }
    setBusy(true);
    try {
      await fleetService.recalculateMaintenanceRisk(selectedVehicle.id);
      await reload();
      showToast({ tone: "success", title: "Assessment updated", message: `${selectedVehicle.registrationNumber} now uses the latest operating evidence.` });
    } catch (reason) {
      setDialogError(
        reason instanceof Error
          ? reason.message
          : "Unable to recalculate maintenance risk",
      );
    } finally {
      setBusy(false);
    }
  };

  const requestReview = async () => {
    if (!selectedVehicle) return;
    setBusy(true);
    try {
      await fleetService.recalculateMaintenanceRisk(selectedVehicle.id, {
        requestReview: true,
      });
      await reload();
    } catch (reason) {
      setDialogError(
        reason instanceof Error
          ? reason.message
          : "Unable to request engineering review",
      );
    } finally {
      setBusy(false);
    }
  };

  const runWorkflowAction = async () => {
    if (!selectedVehicle || !workflow) return;
    if (workflow.action === "run_assessment") return recalculate();
    if (workflow.action === "complete_profile") return navigate(`/vehicles/${selectedVehicle.id}`);
    if (workflow.action === "open_inspection_queue") return navigate("/maintenance/inspections");
    if (workflow.action === "import_history") return navigate(`/vehicles/${selectedVehicle.id}?tab=maintenance`);
    if (workflow.action === "review_assessment" && selectedReview) { setShowReview(true); return; }
    if (workflow.action === "open_work_order") {
      if (selectedReviewId && canManageMaintenance) setShowMaintenance(true);
      else navigate("/maintenance/work-orders");
      return;
    }
    if (workflow.action === "start_inspection") {
      setBusy(true);
      try {
        await fleetService.createCommissioningInspection(selectedVehicle.id);
        await reload();
        navigate("/maintenance/inspections");
      } catch (reason) {
        setDialogError(reason instanceof Error ? reason.message : "Unable to start the initial inspection");
      } finally {
        setBusy(false);
      }
      return;
    }
    setShowRequirements(true);
  };

  if (loading)
    return <LoadingState label="Loading maintenance intelligence..." />;
  if (error || !data)
    return (
      <ErrorState
        message={error ?? "Unable to load predictive maintenance data"}
        onRetry={reload}
      />
    );

  const { critical, held, goodQuality } = fleetRisk;
  const loaded =
    data.status.available && data.status.loaded && !data.status.degraded;

  return (
    <div className="min-w-0">
      <PageHeader
        action={
          <div className="flex flex-wrap gap-2">
            <OperationalInfo
              active={!loaded}
              severity={loaded ? "info" : "warning"}
              title="Maintenance intelligence status"
            >
              Risk is derived from mileage, trip usage, inspections, and
              completed maintenance history. Missing history is listed in each
              vehicle&apos;s data quality details.
            </OperationalInfo>
            {canRunAssessment && <span title={!selectedVehicle ? "Select a vehicle row before running risk calculation" : workflow?.description}>
              <PrimaryButton
                disabled={busy || eligibilityLoading || !selectedVehicle || !workflow?.runnable || !loaded}
                onClick={recalculate}
              >
                <RefreshCw
                  className={`h-4 w-4 ${busy ? "animate-spin motion-reduce:animate-none" : ""}`}
                />
                {busy ? "Calculating risk..." : !selectedVehicle ? "Select vehicle to calculate" : workflow?.runnable ? workflow.label : "Risk calculation unavailable"}
              </PrimaryButton>
            </span>}
          </div>
        }
        description="Prioritize vehicles using server-derived mileage, trip, inspection, and maintenance history."
        eyebrow={
          <StatusBadge tone={loaded ? "green" : "amber"}>
            {loaded ? "Model ready" : "Model degraded"}
          </StatusBadge>
        }
        title="Predictive Maintenance"
      />
      {!selectedVehicle && canRunAssessment && (
        <div className="mb-5 flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm font-semibold text-blue-900">
          <ClipboardCheck className="h-5 w-5 shrink-0 text-blue-700" />
          Select one vehicle row below before running a risk assessment.
        </div>
      )}
      {held > 0 && (
        <div className="mb-5 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800">
          <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <strong>
              {held} vehicle{held === 1 ? "" : "s"} held for engineering review.
            </strong>
            <div className="mt-1 font-medium text-red-700">
              Dispatch remains blocked until an authorized reviewer clears the
              snapshot or confirms maintenance work.
            </div>
          </div>
        </div>
      )}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={ShieldAlert}
          label="Critical vehicles"
          tone={critical ? "red" : "green"}
          trend="Latest snapshot"
          value={String(critical)}
        />
        <MetricCard
          icon={Activity}
          label="Review holds"
          tone={held ? "red" : "green"}
          trend="Dispatch policy"
          value={String(held)}
        />
        <MetricCard
          icon={DatabaseZap}
          label="Good data quality"
          tone="blue"
          trend={`${fleetRisk.evaluated} evaluated`}
          value={String(goodQuality)}
        />
        <MetricCard
          icon={Gauge}
          label="Fleet evaluated"
          tone="green"
          trend="Latest snapshot"
          value={String(fleetRisk.evaluated)}
        />
      </div>

      <div className="mt-5 grid min-w-0 gap-5 2xl:grid-cols-[minmax(0,1.6fr)_380px]">
        <section className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-extrabold text-slate-950">
                Fleet risk queue
              </h2>
              <p className="text-sm text-slate-500">
                Select a vehicle to review its current prediction.
              </p>
            </div>
            <label className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 sm:max-w-xs">
              <Search className="h-4 w-4 text-slate-400" />
              <input
                aria-label="Search predictive vehicles"
                className="min-w-0 flex-1 outline-none"
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Registration or fleet code"
                value={query}
              />
            </label>
          </div>
          {rows.length ? (
            <DataTable
              headers={[
                "Vehicle",
                "30-day risk",
                "2,000-km risk",
                "Risk level",
                "Inspection focus",
                "Data",
                "Review",
              ]}
            >
              {rows.map((vehicle) => {
                const prediction = latestByVehicle.get(vehicle.id);
                const selected = selectedVehicle?.id === vehicle.id;
                return (
                  <tr
                    aria-selected={selected}
                    className={`cursor-pointer transition hover:bg-blue-50/60 ${selected ? "bg-blue-50" : ""}`}
                    key={vehicle.id}
                    onClick={() => setSelectedVehicleId(vehicle.id)}
                    tabIndex={0}
                    onKeyDown={(event) =>
                      event.key === "Enter" && setSelectedVehicleId(vehicle.id)
                    }
                  >
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-3">
                        <span aria-hidden="true" className={`grid h-5 w-5 shrink-0 place-items-center rounded-full border-2 ${selected ? "border-blue-600" : "border-slate-300"}`}>
                          {selected && <span className="h-2.5 w-2.5 rounded-full bg-blue-600" />}
                        </span>
                        <div><div className="font-extrabold text-slate-950">
                        {vehicle.registrationNumber}
                        </div>
                        <div className="text-xs font-semibold text-slate-500">
                        {vehicle.vehicleCode} · {vehicle.category}
                        </div></div>
                      </div>
                    </td>
                    <td className="px-5 py-4 font-extrabold">
                      {probability(prediction?.probability30Days)}
                    </td>
                    <td className="px-5 py-4 font-extrabold">
                      {probability(prediction?.probability2000Km)}
                    </td>
                    <td className="px-5 py-4">
                      {prediction ? (
                        <RiskBadge risk={prediction.risk} />
                      ) : (
                        <StatusBadge tone="slate">Not evaluated</StatusBadge>
                      )}
                    </td>
                    <td className="px-5 py-4 font-semibold">
                      {prediction?.systemRisks
                        .slice(0, 2)
                        .map((item) => item.name)
                        .join(", ") || "Inspection history needed"}
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge
                        tone={
                          prediction?.dataQuality === "good"
                            ? "green"
                            : prediction
                              ? "amber"
                              : "slate"
                        }
                      >
                        {prediction?.dataQuality || "Unknown"}
                      </StatusBadge>
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge
                        tone={
                          prediction?.dispatchHold
                            ? "red"
                            : prediction?.reviewStatus === "cleared"
                              ? "green"
                              : "slate"
                        }
                      >
                        {prediction?.reviewStatus.replaceAll("_", " ") ||
                          "Not required"}
                      </StatusBadge>
                    </td>
                  </tr>
                );
              })}
            </DataTable>
          ) : (
            <EmptyState
              description="Adjust the search or add an eligible vehicle."
              title="No matching vehicles"
            />
          )}
        </section>

        <aside className="min-w-0 rounded-lg border border-slate-200 bg-white shadow-card">
          <div className="border-b border-slate-200 p-5">
            <h2 className="font-extrabold text-slate-950">
              Current risk snapshot
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {selectedVehicle?.registrationNumber ?? "Select a vehicle"}
            </p>
          </div>
          {selectedVehicle && (
            <div className="border-b border-slate-200 p-5">
              {eligibilityLoading ? (
                <div className="flex items-center gap-3 text-sm font-semibold text-slate-600">
                  <RefreshCw className="h-4 w-4 animate-spin motion-reduce:animate-none" />
                  Checking assessment workflow...
                </div>
              ) : eligibilityError || !workflow ? (
                <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800">
                  <AlertTriangle className="h-5 w-5 shrink-0" />
                  {eligibilityError || "Assessment workflow is unavailable."}
                </div>
              ) : (
                <div className={`rounded-lg border p-4 ${workflow.tone === "red" ? "border-red-200 bg-red-50" : workflow.tone === "amber" ? "border-amber-200 bg-amber-50" : workflow.tone === "green" ? "border-emerald-200 bg-emerald-50" : "border-blue-200 bg-blue-50"}`}>
                  <div className="flex items-start gap-3">
                    {workflow.tone === "green" ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-700" /> : <ClipboardCheck className={`mt-0.5 h-5 w-5 shrink-0 ${workflow.tone === "red" ? "text-red-700" : workflow.tone === "amber" ? "text-amber-700" : "text-blue-700"}`} />}
                    <div className="min-w-0 flex-1">
                      <div className="font-extrabold text-slate-950">{workflow.label}</div>
                      <p className="mt-1 text-sm font-medium text-slate-700">{workflow.description}</p>
                      {workflow.action !== "none" && (
                        <button
                          className="mt-3 inline-flex min-h-10 items-center justify-center rounded-lg bg-slate-950 px-3 text-sm font-bold text-white transition hover:bg-slate-800 disabled:opacity-50"
                          disabled={busy}
                          onClick={runWorkflowAction}
                          type="button"
                        >
                          {busy ? "Working..." : workflow.label}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
          {selectedVehicle && selectedPrediction ? (
            <div className="space-y-5 p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <RiskBadge risk={selectedPrediction.risk} />
                <StatusBadge
                  tone={selectedPrediction.dispatchHold ? "red" : "green"}
                >
                  {selectedPrediction.dispatchHold
                    ? "Dispatch held"
                    : "Dispatch policy clear"}
                </StatusBadge>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <SnapshotValue
                  label="30 days"
                  value={probability(selectedPrediction.probability30Days)}
                />
                <SnapshotValue
                  label="2,000 km"
                  value={probability(selectedPrediction.probability2000Km)}
                />
              </div>
              <div>
                <div className="text-xs font-bold uppercase text-slate-500">
                  Top inspection areas
                </div>
                <div className="mt-2 space-y-2">
                  {selectedPrediction.systemRisks.slice(0, 3).map((risk) => (
                    <div
                      className="flex items-center justify-between gap-3 border-b border-slate-100 pb-2"
                      key={risk.key}
                    >
                      <span className="font-semibold">{risk.name}</span>
                      <span className="text-sm font-bold">
                        {probability(risk.probability)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2 text-xs font-bold uppercase text-slate-500">
                  <CalendarClock className="h-4 w-4" />
                  Planning range
                </div>
                <p className="mt-2 text-sm font-semibold text-slate-800">
                  {planningLabel(selectedPrediction)}
                </p>
              </div>
              <div>
                <div className="flex items-center gap-2 text-xs font-bold uppercase text-slate-500">
                  <History className="h-4 w-4" />
                  Freshness and quality
                </div>
                <p className="mt-2 text-sm font-semibold">
                  {selectedPrediction.createdAt
                    ? new Date(selectedPrediction.createdAt).toLocaleString()
                    : "No timestamp"}{" "}
                  · {selectedPrediction.dataQuality}
                </p>
                {selectedPrediction.defaultedFields.length > 0 && (
                  <p className="mt-1 text-xs text-amber-700">
                    {selectedPrediction.defaultedFields.length} field
                    {selectedPrediction.defaultedFields.length === 1 ? "" : "s"}{" "}
                    defaulted
                  </p>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                <Link
                  className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm font-bold hover:bg-slate-50"
                  to={`/vehicles/${selectedVehicle.id}`}
                >
                  <History className="h-4 w-4" />
                  History
                </Link>
                {canRunAssessment && <button
                  className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm font-bold transition hover:bg-blue-50 disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={busy || selectedPrediction.reviewStatus === "pending"}
                  onClick={requestReview}
                  type="button"
                >
                  <ClipboardCheck className="h-4 w-4" />
                  {selectedPrediction.reviewStatus === "pending"
                    ? "Review pending"
                    : "Request Review"}
                </button>}
                {canManageMaintenance && <button
                  className="inline-flex min-h-10 items-center gap-2 rounded-lg bg-blue-600 px-3 text-sm font-bold text-white transition hover:bg-blue-700"
                  onClick={() => setShowMaintenance(true)}
                  type="button"
                >
                  <Wrench className="h-4 w-4" />
                  Create Maintenance
                </button>}
              </div>
            </div>
          ) : (
            <div className="p-5">
              <EmptyState
                description={selectedVehicle ? "Follow the required action above to establish this vehicle's first risk snapshot." : "Choose one row from the fleet risk queue to view its workflow and current prediction."}
                title={selectedVehicle ? "No current prediction" : "No vehicle selected"}
              />
            </div>
          )}
        </aside>
      </div>

      <Card className="mt-5" title="Recent prediction history">
        {data.predictions.length ? (
          <div className="divide-y divide-slate-100">
            {data.predictions.slice(0, 8).map((item) => (
              <div
                className="flex flex-wrap items-center justify-between gap-3 py-3"
                key={item.id}
              >
                <div>
                  <div className="font-bold">{item.vehicleRegistration}</div>
                  <div className="text-xs text-slate-500">
                    {item.createdAt
                      ? new Date(item.createdAt).toLocaleString()
                      : "Timestamp unavailable"}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-bold">
                    30d {probability(item.probability30Days)}
                  </span>
                  <RiskBadge risk={item.risk} />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyState
            description="Risk history appears after a vehicle is evaluated."
            title="No prediction history"
          />
        )}
      </Card>
      {showMaintenance && selectedVehicle && (
        <MaintenanceRecordDialog
          onClose={() => setShowMaintenance(false)}
          onSaved={reload}
          predictionReviewId={selectedReviewId || undefined}
          vehicle={selectedVehicle}
        />
      )}
      {showReview && selectedReview && (
        <PredictionReviewDialog
          onClose={() => setShowReview(false)}
          onResolved={reload}
          review={selectedReview}
        />
      )}
      {showRequirements && eligibility && selectedVehicle && (
        <ModalViewport>
          <ModalPanel aria-modal="true" className="max-w-lg" role="dialog">
            <ModalHeader className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-6 w-6 shrink-0 text-amber-600" />
                <div>
                  <h2 className="text-xl font-extrabold">More operating records are required</h2>
                  <p className="mt-1 text-sm text-slate-500">{selectedVehicle.registrationNumber} cannot be assessed yet.</p>
                </div>
              </div>
              <button aria-label="Close requirements" className="rounded-lg p-2 hover:bg-slate-100" onClick={() => setShowRequirements(false)} type="button"><X className="h-5 w-5" /></button>
            </ModalHeader>
            <ModalBody className="space-y-3">
              {eligibility.blockingReasons.map((reason) => <div className="flex gap-3 rounded-lg bg-amber-50 p-3 text-sm font-semibold text-amber-950" key={reason}><AlertTriangle className="h-5 w-5 shrink-0 text-amber-600" />{reason}</div>)}
              {eligibility.onboardingType === "brand_new" && eligibility.status === "building_history" && (
                <div className="grid grid-cols-2 gap-3">
                  <SnapshotValue label="Completed trips" value={`${eligibility.requirements.completedTrips.current}/${eligibility.requirements.completedTrips.required}`} />
                  <SnapshotValue label="Distance recorded" value={`${eligibility.requirements.recordedDistanceKm.current}/${eligibility.requirements.recordedDistanceKm.required} km`} />
                </div>
              )}
              <p className="text-sm text-slate-600">Complete the listed evidence or select another vehicle that is ready for assessment.</p>
            </ModalBody>
            <ModalFooter>
              <SecondaryButton onClick={() => { setShowRequirements(false); setSelectedVehicleId(""); }}>Select another vehicle</SecondaryButton>
              <PrimaryButton onClick={() => navigate(`/vehicles/${selectedVehicle.id}?tab=risk-assessment`)}>View vehicle requirements</PrimaryButton>
            </ModalFooter>
          </ModalPanel>
        </ModalViewport>
      )}
      {dialogError && (
        <ModalViewport>
          <ModalPanel aria-modal="true" className="max-w-md" role="alertdialog">
            <ModalHeader className="flex items-start gap-3"><AlertTriangle className="mt-0.5 h-6 w-6 shrink-0 text-red-600" /><div><h2 className="text-xl font-extrabold">Assessment action could not be completed</h2><p className="mt-1 text-sm text-slate-500">Review the guidance before trying again.</p></div></ModalHeader>
            <ModalBody><p className="rounded-lg bg-red-50 p-4 text-sm font-semibold text-red-800">{dialogError}</p></ModalBody>
            <ModalFooter><PrimaryButton onClick={() => setDialogError("")}>Close</PrimaryButton></ModalFooter>
          </ModalPanel>
        </ModalViewport>
      )}
    </div>
  );
}

function probability(value?: number) {
  return value === undefined ? "—" : `${Math.round(value * 100)}%`;
}
function SnapshotValue({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <div className="text-xs font-bold uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-extrabold">{value}</div>
    </div>
  );
}
function planningLabel(prediction: MaintenancePrediction) {
  if (prediction.planningStatus === "no_near_term_failure_indicated")
    return "No near-term failure indicated.";
  const window = prediction.planningWindow;
  if (!window)
    return "Planning range withheld until sufficient history is available.";
  const days =
    window.minimumDays !== undefined || window.maximumDays !== undefined
      ? `${window.minimumDays ?? 0}–${window.maximumDays ?? "—"} days`
      : "";
  const km =
    window.minimumKm !== undefined || window.maximumKm !== undefined
      ? `${window.minimumKm ?? 0}–${window.maximumKm ?? "—"} km`
      : "";
  return (
    [days, km].filter(Boolean).join(" or ") || "Planning range unavailable."
  );
}
