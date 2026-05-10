import 'package:flutter/material.dart';

import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../models/driver_models.dart';
import '../../widgets/fleet_widgets.dart';

class HomeDashboard extends StatelessWidget {
  const HomeDashboard({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    final nextStop = controller.route.stops.firstWhere(
      (stop) => stop.status != DeliveryStatus.delivered,
      orElse: () => controller.route.stops.last,
    );
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
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
                'Next stop: ${nextStop.customer}',
                style: const TextStyle(color: AppColors.muted),
              ),
              const SizedBox(height: 16),
              FleetButton(
                label: controller.tripActive ? 'End trip' : 'Start trip',
                icon: controller.tripActive
                    ? Icons.stop_circle_outlined
                    : Icons.play_circle_outline,
                danger: controller.tripActive,
                onPressed: controller.toggleTrip,
              ),
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
