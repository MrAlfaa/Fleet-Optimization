import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../models/driver_models.dart';
import '../../widgets/fleet_widgets.dart';

class StopDetailScreen extends StatelessWidget {
  const StopDetailScreen({super.key, required this.stopId});

  final String stopId;

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    final stop = controller.route.stops.firstWhere((item) => item.id == stopId);
    return Scaffold(
      appBar: AppBar(title: const Text('Stop detail')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          FleetCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    StatusPill(
                      label: stop.priority,
                      color: stop.priority == 'Critical'
                          ? AppColors.critical
                          : AppColors.warning,
                    ),
                    const Spacer(),
                    StatusPill(
                      label: deliveryStatusLabel(stop.status),
                      color: deliveryStatusColor(stop.status),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  stop.customer,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w900,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  stop.address,
                  style: const TextStyle(color: AppColors.muted),
                ),
                const SizedBox(height: 12),
                Text(
                  'ETA ${stop.eta} - ${stop.zone}',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          FleetButton(
            label: 'Launch Google Maps',
            icon: Icons.navigation_outlined,
            onPressed: () => _launchMaps(stop.latitude, stop.longitude),
          ),
          const SizedBox(height: 14),
          Text(
            'Update delivery status',
            style: Theme.of(
              context,
            ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 10),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: DeliveryStatus.values.map((status) {
              return FleetButton(
                label: deliveryStatusLabel(status),
                filled: status == stop.status,
                onPressed: () {
                  controller.updateStopStatus(stop.id, status);
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                        '${stop.customer} marked ${deliveryStatusLabel(status).toLowerCase()}',
                      ),
                    ),
                  );
                },
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Future<void> _launchMaps(double latitude, double longitude) async {
    final uri = Uri.parse(
      'https://www.google.com/maps/dir/?api=1&destination=$latitude,$longitude',
    );
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }
}
