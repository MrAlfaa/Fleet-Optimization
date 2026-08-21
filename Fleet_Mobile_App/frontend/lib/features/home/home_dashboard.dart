import 'package:flutter/material.dart';

import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/fleet_widgets.dart';
import '../trip/trip_inspection_sheet.dart';

class HomeDashboard extends StatelessWidget {
  const HomeDashboard({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    if (!controller.route.hasAssignedRoute) {
      return ListView(
        padding: const EdgeInsets.all(16),
        children: [
          FleetCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                StatusPill(label: 'NO ROUTE', color: AppColors.warning),
                const SizedBox(height: 14),
                Text(
                  'No assigned route',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 8),
                Text(
                  controller.error ??
                      'A dispatched backend route assigned to this driver will appear here.',
                  style: const TextStyle(color: AppColors.muted),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          FleetCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Vehicle assignment',
                  style: TextStyle(fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 8),
                StatusPill(
                  label: controller.vehicle.modelStatus,
                  color: AppColors.primary,
                ),
                const SizedBox(height: 10),
                Text(
                  controller.vehicle.riskSummary,
                  style: const TextStyle(color: AppColors.muted),
                ),
              ],
            ),
          ),
        ],
      );
    }
    final nextStop = controller.route.nextStop;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        FleetCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Expanded(
                    child: Text(
                      'Pre-trip readiness',
                      style: TextStyle(fontWeight: FontWeight.w900),
                    ),
                  ),
                  StatusPill(
                    label: controller.readiness.canStart
                        ? controller.readiness.vehicleStatus.toUpperCase()
                        : 'BLOCKED',
                    color: controller.readiness.canStart
                        ? AppColors.warning
                        : AppColors.critical,
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                controller.readiness.vehicleRegistration,
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
              ),
              Text(
                controller.readiness.vehicleCategory.replaceAll('_', ' '),
                style: const TextStyle(color: AppColors.muted),
              ),
              const SizedBox(height: 12),
              Text(
                'Maintenance risk: ${controller.readiness.maintenanceRisk}  ·  Route delay: ${controller.readiness.routeDelayRisk}',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              Text(
                'Route distance: ${controller.readiness.routeDistanceKm.toStringAsFixed(1)} km',
                style: const TextStyle(color: AppColors.muted),
              ),
              if (controller.readiness.demandLevels.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(
                    'Zone demand: ${controller.readiness.demandLevels.join(', ')}',
                    style: const TextStyle(
                      color: AppColors.warning,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ...controller.readiness.blockingReasons.map(
                (reason) => Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    '$reason. Contact the fleet manager.',
                    style: const TextStyle(
                      color: AppColors.critical,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ),
              ...controller.readiness.warnings.map(
                (warning) => Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    warning,
                    style: const TextStyle(
                      color: AppColors.warning,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        FleetCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  StatusPill(
                    label: controller.tripActive ? 'TRIP ACTIVE' : 'READY',
                    color: controller.tripActive
                        ? AppColors.success
                        : AppColors.primary,
                  ),
                  const Spacer(),
                  Text(
                    controller.route.eta,
                    style: const TextStyle(fontWeight: FontWeight.w900),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Text(
                controller.route.title,
                style: Theme.of(
                  context,
                ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 6),
              Text(
                nextStop == null
                    ? 'All assigned stops have been processed'
                    : 'Next stop: ${nextStop.customer} · ${nextStop.zone}',
                style: const TextStyle(color: AppColors.muted),
              ),
              const SizedBox(height: 16),
              FleetButton(
                label: controller.loading
                    ? 'Updating trip...'
                    : controller.tripActive
                    ? nextStop == null
                          ? 'End trip'
                          : 'Process all stops before ending'
                    : 'Start trip',
                icon: controller.tripActive
                    ? Icons.stop_circle_outlined
                    : Icons.play_circle_outline,
                danger: controller.tripActive,
                onPressed:
                    controller.loading ||
                        (controller.tripActive && nextStop != null) ||
                        (!controller.tripActive &&
                            !controller.readiness.canStart)
                    ? null
                    : () async {
                        if (controller.tripActive) {
                          final inspection = await showPostTripInspectionSheet(
                            context,
                            initialMileage: controller.vehicle.mileage
                                .toDouble(),
                          );
                          if (inspection != null) {
                            await controller.endTripWithInspection(inspection);
                          }
                          return;
                        }
                        final inspection = await showPreTripInspectionSheet(
                          context,
                          initialMileage: controller.vehicle.mileage.toDouble(),
                        );
                        if (inspection != null) {
                          await controller.startTripWithInspection(inspection);
                        }
                      },
              ),
              if (controller.locationSharingUnavailable) ...[
                const SizedBox(height: 10),
                const Text(
                  'Location sharing unavailable. Trip is active without live GPS updates.',
                  style: TextStyle(
                    color: AppColors.warning,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 14),
        Row(
          children: [
            MetricTile(
              label: 'Stops done',
              value:
                  '${controller.route.completedStops}/${controller.route.stops.length}',
              icon: Icons.check_circle_outline,
              color: AppColors.success,
            ),
            const SizedBox(width: 10),
            MetricTile(
              label: 'Distance',
              value:
                  '${controller.route.totalDistanceKm.toStringAsFixed(1)} km',
              icon: Icons.timeline_rounded,
            ),
          ],
        ),
        const SizedBox(height: 14),
        FleetCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Vehicle risk notice',
                style: TextStyle(fontWeight: FontWeight.w900),
              ),
              const SizedBox(height: 8),
              StatusPill(
                label: controller.vehicle.modelStatus,
                color: AppColors.primary,
              ),
              const SizedBox(height: 10),
              Text(
                controller.vehicle.riskSummary,
                style: const TextStyle(color: AppColors.muted),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Text(
          'Trip event timeline',
          style: Theme.of(
            context,
          ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 10),
        ...controller.tripEvents.map(
          (event) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: FleetCard(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  CircleAvatar(
                    radius: 17,
                    backgroundColor: severityColor(
                      event.type,
                    ).withValues(alpha: 0.14),
                    child: Icon(
                      Icons.fiber_manual_record,
                      size: 12,
                      color: severityColor(event.type),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${event.time}  ${event.title}',
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          event.description,
                          style: const TextStyle(color: AppColors.muted),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }
}
