import {
  Activity,
  CalendarClock,
  ClipboardCheck,
  DatabaseZap,
  Gauge,
  History,
  RefreshCw,
  Search,
  ShieldAlert,
  Wrench,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
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
  StatusBadge,
} from "../components/UI";
import { MaintenanceRecordDialog } from "../components/MaintenanceRecordDialog";
import { summarizeLatestFleetRisk } from "../features/predictive/maintenanceRisk";
import { useAsyncData } from "../hooks/useAsyncData";
import { fleetService } from "../services/fleetService";
import { authService } from "../services/authService";
import { canAccess } from "../utils/permissions";
import type { MaintenancePrediction } from "../types";

export function PredictiveRiskPage() {
  const currentUser = authService.getSession();
  const canRunAssessment = canAccess(currentUser, "predictive.run");
  const canManageMaintenance = canAccess(currentUser, "maintenance.manage");
  const [query, setQuery] = useState("");
  const [selectedVehicleId, setSelectedVehicleId] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
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
  const selectedVehicle =
    rows.find((vehicle) => vehicle.id === selectedVehicleId) ?? rows[0];
  const selectedPrediction = selectedVehicle
    ? latestByVehicle.get(selectedVehicle.id)
    : undefined;
  const selectedReviewId =
    selectedPrediction?.reviewId ||
    data?.reviews.find(
      (review) => review.predictionId === selectedPrediction?.id,
    )?.id ||
    "";

  const recalculate = async () => {
    if (!selectedVehicle) return;
    setBusy(true);
    setActionError("");
    try {
      await fleetService.recalculateMaintenanceRisk(selectedVehicle.id);
      await reload();
    } catch (reason) {
      setActionError(
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
    setActionError("");
    try {
      await fleetService.recalculateMaintenanceRisk(selectedVehicle.id, {
        requestReview: true,
      });
      await reload();
    } catch (reason) {
      setActionError(
        reason instanceof Error
          ? reason.message
          : "Unable to request engineering review",
      );
    } finally {
      setBusy(false);
    }
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
            {canRunAssessment && <PrimaryButton
              disabled={busy || !selectedVehicle || !loaded}
              onClick={recalculate}
            >
              <RefreshCw
                className={`h-4 w-4 ${busy ? "animate-spin motion-reduce:animate-none" : ""}`}
              />
              {busy ? "Recalculating..." : "Recalculate Risk"}
            </PrimaryButton>}
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
      {actionError && (
        <div
          className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700"
          role="alert"
        >
          {actionError}
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
                      <div className="font-extrabold text-slate-950">
                        {vehicle.registrationNumber}
                      </div>
                      <div className="text-xs font-semibold text-slate-500">
                        {vehicle.vehicleCode} · {vehicle.category}
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
                description="Run a server-derived calculation to establish the first risk snapshot."
                title="No current prediction"
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
