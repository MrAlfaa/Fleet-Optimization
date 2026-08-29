import 'package:flutter/material.dart';

import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../models/driver_models.dart';
import '../../widgets/fleet_widgets.dart';
import 'assigned_route_map.dart';
import 'stop_detail_screen.dart';

class FleetNavigationScreen extends StatelessWidget {
  const FleetNavigationScreen({super.key, this.showTiles = true});

  final bool showTiles;

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);

    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        final stop = controller.route.nextStop;
        final navigation = controller.route.navigation;
        final currentLocation = controller.currentLocation;

        return Scaffold(
          appBar: AppBar(title: const Text('FleetOpt navigation')),
          body: stop == null
              ? const Padding(
                  padding: EdgeInsets.all(16),
                  child: FleetCard(
                    child: Text('All assigned parcel stops are processed.'),
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    SizedBox(
                      height: 390,
                      child: AssignedRouteMap(
                        route: controller.route,
                        geometry: controller.routeGeometry,
                        currentLocation: currentLocation == null
                            ? null
                            : RouteCoordinate(
                                latitude: currentLocation.latitude,
                                longitude: currentLocation.longitude,
                              ),
                        showTiles: showTiles,
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
                                label: navigation.status == 'arrived'
                                    ? 'ARRIVED'
                                    : navigation.isNavigating
                                    ? 'NAVIGATING'
                                    : 'NEXT STOP',
                                color: navigation.status == 'arrived'
                                    ? AppColors.warning
                                    : AppColors.success,
                              ),
                              const Spacer(),
                              Text(
                                'Stop ${stop.sequence}/${controller.route.assignedStopCount}',
                                style: const TextStyle(
                                  fontWeight: FontWeight.w900,
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 14),
                          Text(
                            stop.customer,
                            style: Theme.of(context).textTheme.titleLarge
                                ?.copyWith(fontWeight: FontWeight.w900),
                          ),
                          const SizedBox(height: 5),
                          Text(
                            'Parcel ${stop.parcelCode.isEmpty ? stop.id : stop.parcelCode}',
                            style: const TextStyle(fontWeight: FontWeight.w800),
                          ),
                          const SizedBox(height: 5),
                          Text(
                            '${stop.address}\n${stop.zone}',
                            style: const TextStyle(color: AppColors.muted),
                          ),
                          if (controller.locationSharingUnavailable) ...[
                            const SizedBox(height: 10),
                            const Text(
                              'GPS is unavailable. Delivery actions remain available, but Live Trips cannot update the vehicle position.',
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
                    if (!navigation.isNavigating)
                      FleetButton(
                        label: 'Start navigation to this parcel',
                        icon: Icons.navigation_rounded,
                        onPressed: () async {
                          await controller.startNavigationToStop(stop.id);
                        },
                      )
                    else if (navigation.status != 'arrived')
                      FleetButton(
                        label: 'Mark arrived',
                        icon: Icons.location_on_rounded,
                        onPressed: () async {
                          await controller.updateStopStatus(
                            stop.id,
                            DeliveryStatus.arrived,
                          );
                        },
                      )
                    else
                      FleetButton(
                        label: 'Confirm parcel delivered',
                        icon: Icons.check_circle_outline_rounded,
                        onPressed: () async {
                          await controller.updateStopStatus(
                            stop.id,
                            DeliveryStatus.delivered,
                          );
                        },
                      ),
                    const SizedBox(height: 10),
                    FleetButton(
                      label: 'View parcel and exception actions',
                      icon: Icons.inventory_2_outlined,
                      filled: false,
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => StopDetailScreen(stopId: stop.id),
                        ),
                      ),
                    ),
                  ],
                ),
        );
      },
    );
  }
}
