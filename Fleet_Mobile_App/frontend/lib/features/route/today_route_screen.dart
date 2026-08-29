import 'package:flutter/material.dart';

import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../models/driver_models.dart';
import '../../widgets/fleet_widgets.dart';
import 'assigned_route_map.dart';
import 'fleet_navigation_screen.dart';
import 'stop_detail_screen.dart';

class TodayRouteScreen extends StatelessWidget {
  const TodayRouteScreen({super.key});

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
                StatusPill(label: 'WAITING', color: AppColors.warning),
                const SizedBox(height: 14),
                Text(
                  'No dispatched route assigned',
                  style: Theme.of(
                    context,
                  ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 8),
                Text(
                  controller.error ??
                      'Route plans assigned to this driver from the backend dispatch workflow will be listed here.',
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
          padding: EdgeInsets.zero,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                height: 240,
                child: AssignedRouteMap(
                  route: controller.route,
                  geometry: controller.routeGeometry,
                  currentLocation: controller.currentLocation == null
                      ? null
                      : RouteCoordinate(
                          latitude: controller.currentLocation!.latitude,
                          longitude: controller.currentLocation!.longitude,
                        ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      controller.route.title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Origin: ${controller.route.depot}',
                      style: const TextStyle(color: AppColors.muted),
                    ),
                    const SizedBox(height: 12),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        StatusPill(
                          label:
                              '${controller.route.assignedStopCount} assigned stops',
                          color: AppColors.primary,
                        ),
                        StatusPill(
                          label:
                              '${controller.route.totalDistanceKm.toStringAsFixed(1)} km',
                          color: AppColors.success,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        if (nextStop != null) ...[
          FleetCard(
            child: InkWell(
              onTap: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => StopDetailScreen(stopId: nextStop.id),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      StatusPill(label: 'NEXT STOP', color: AppColors.success),
                      const Spacer(),
                      Text(
                        nextStop.eta,
                        style: const TextStyle(fontWeight: FontWeight.w900),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Text(
                    nextStop.customer,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Parcel ${nextStop.parcelCode.isEmpty ? nextStop.id : nextStop.parcelCode} - Stop ${nextStop.sequence}',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${nextStop.address}\n${nextStop.zone}',
                    style: const TextStyle(color: AppColors.muted),
                  ),
                  if (nextStop.parcelWeightKg != null ||
                      nextStop.handling.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(
                      [
                        if (nextStop.parcelWeightKg != null)
                          '${nextStop.parcelWeightKg!.toStringAsFixed(1)} kg',
                        if (nextStop.handling.isNotEmpty)
                          nextStop.handling.join(', '),
                      ].join(' - '),
                      style: const TextStyle(
                        color: AppColors.muted,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                  const SizedBox(height: 12),
                  FleetButton(
                    label: 'Start FleetOpt navigation',
                    icon: Icons.navigation_rounded,
                    onPressed: () async {
                      final started = await controller.startNavigationToStop(
                        nextStop.id,
                      );
                      if (!context.mounted) return;
                      if (started) {
                        await Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => const FleetNavigationScreen(),
                          ),
                        );
                      } else {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(
                              controller.error ?? 'Unable to start navigation.',
                            ),
                          ),
                        );
                      }
                    },
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
        ],
        FleetButton(
          label: 'Open FleetOpt route navigator',
          icon: Icons.map_outlined,
          onPressed: () => Navigator.of(context).push(
            MaterialPageRoute(builder: (_) => const FleetNavigationScreen()),
          ),
        ),
        if (controller.route.deliveryDate.isNotEmpty) ...[
          const SizedBox(height: 10),
          FleetCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${controller.route.deliveryDate} · ${controller.route.deliveryPeriod == 'second_half' ? 'Second Half (13:00–17:00)' : 'First Half (08:00–12:00)'}',
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                if (controller.route.consolidationId.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    'Consolidation ${controller.route.consolidationId} · Load ${controller.route.loadId}',
                    style: const TextStyle(
                      color: AppColors.muted,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
        const SizedBox(height: 16),
        Text(
          'Stop order',
          style: Theme.of(
            context,
          ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 10),
        ...controller.route.stops.map(
          (stop) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: FleetCard(
              child: InkWell(
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => StopDetailScreen(stopId: stop.id),
                  ),
                ),
                child: Row(
                  children: [
                    CircleAvatar(
                      backgroundColor: AppColors.primary.withValues(
                        alpha: 0.12,
                      ),
                      foregroundColor: AppColors.primary,
                      child: Text(
                        '${stop.sequence}',
                        style: const TextStyle(fontWeight: FontWeight.w900),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            stop.customer,
                            style: const TextStyle(fontWeight: FontWeight.w900),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${stop.eta} - ${stop.zone}',
                            style: const TextStyle(color: AppColors.muted),
                          ),
                        ],
                      ),
                    ),
                    StatusPill(
                      label: stop.id == nextStop?.id
                          ? 'NEXT'
                          : deliveryStatusLabel(stop.status),
                      color: stop.id == nextStop?.id
                          ? AppColors.success
                          : deliveryStatusColor(stop.status),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
