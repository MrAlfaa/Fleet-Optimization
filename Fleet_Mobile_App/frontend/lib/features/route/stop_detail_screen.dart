import 'package:flutter/material.dart';

import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../models/driver_models.dart';
import '../../services/map_navigation_service.dart';
import '../../widgets/fleet_widgets.dart';

class StopDetailScreen extends StatelessWidget {
  const StopDetailScreen({super.key, required this.stopId});

  final String stopId;

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    final matches = controller.route.stops.where((item) => item.id == stopId);
    if (matches.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text('Stop detail')),
        body: const Padding(
          padding: EdgeInsets.all(16),
          child: FleetCard(
            child: Text('This delivery stop is no longer available.'),
          ),
        ),
      );
    }
    final stop = matches.first;
    final canUpdate =
        controller.tripActive && controller.route.nextStop?.id == stop.id;
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
                  'Parcel ${stop.parcelCode.isEmpty ? stop.id : stop.parcelCode}',
                  style: const TextStyle(fontWeight: FontWeight.w900),
                ),
                const SizedBox(height: 6),
                Text(
                  [
                        if (stop.parcelWeightKg != null)
                          '${stop.parcelWeightKg!.toStringAsFixed(1)} kg',
                        if (stop.dimensionsLabel != 'Not recorded')
                          stop.dimensionsLabel,
                        if (stop.handling.isNotEmpty) stop.handling.join(', '),
                      ].isEmpty
                      ? 'Parcel handling details not recorded'
                      : [
                          if (stop.parcelWeightKg != null)
                            '${stop.parcelWeightKg!.toStringAsFixed(1)} kg',
                          if (stop.dimensionsLabel != 'Not recorded')
                            stop.dimensionsLabel,
                          if (stop.handling.isNotEmpty)
                            stop.handling.join(', '),
                        ].join(' - '),
                  style: const TextStyle(color: AppColors.muted),
                ),
                if (stop.customerPhone.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    'Customer contact: ${stop.customerPhone}',
                    style: const TextStyle(color: AppColors.muted),
                  ),
                ],
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
            onPressed: () async {
              final opened = await GoogleMapsNavigation.openStop(stop);
              if (!context.mounted || opened) {
                return;
              }
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Unable to open Google Maps navigation.'),
                ),
              );
            },
          ),
          const SizedBox(height: 14),
          if (!canUpdate) ...[
            FleetCard(
              child: Text(
                controller.tripActive
                    ? 'Complete the current next stop before updating this delivery.'
                    : 'Start the assigned trip before updating delivery status.',
                style: const TextStyle(
                  color: AppColors.warning,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            const SizedBox(height: 14),
          ],
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
            children:
                [
                  DeliveryStatus.pending,
                  DeliveryStatus.arrived,
                  DeliveryStatus.delivered,
                ].map((status) {
                  return FleetButton(
                    label: deliveryStatusLabel(status),
                    filled: status == stop.status,
                    onPressed: canUpdate
                        ? () async {
                            await controller.updateStopStatus(stop.id, status);
                            if (!context.mounted) {
                              return;
                            }
                            if (status == DeliveryStatus.delivered) {
                              final next = controller.route.nextStop;
                              Navigator.of(context).pop();
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(
                                  content: Text(
                                    next == null
                                        ? 'Delivery completed. All assigned stops are processed.'
                                        : 'Delivery completed. Next stop: ${next.customer}.',
                                  ),
                                ),
                              );
                              return;
                            }
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(
                                content: Text(
                                  controller.error ??
                                      '${stop.customer} marked ${deliveryStatusLabel(status).toLowerCase()}',
                                ),
                              ),
                            );
                          }
                        : null,
                  );
                }).toList(),
          ),
          const SizedBox(height: 12),
          FleetButton(
            label: 'Could not deliver',
            icon: Icons.event_repeat_rounded,
            danger: true,
            filled: false,
            onPressed: canUpdate
                ? () => _showIncompleteDialog(context, controller, stop.id)
                : null,
          ),
        ],
      ),
    );
  }

  Future<void> _showIncompleteDialog(
    BuildContext context,
    dynamic controller,
    String orderId,
  ) async {
    String reason = 'customer_unavailable';
    final details = TextEditingController();
    final submitted = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          title: const Text('Reschedule delivery'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                initialValue: reason,
                decoration: const InputDecoration(labelText: 'Reason'),
                items: const [
                  DropdownMenuItem(
                    value: 'customer_unavailable',
                    child: Text('Customer unavailable'),
                  ),
                  DropdownMenuItem(
                    value: 'incorrect_address',
                    child: Text('Incorrect address'),
                  ),
                  DropdownMenuItem(
                    value: 'access_restricted',
                    child: Text('Access restricted'),
                  ),
                  DropdownMenuItem(
                    value: 'parcel_damaged',
                    child: Text('Parcel damaged'),
                  ),
                  DropdownMenuItem(
                    value: 'vehicle_issue',
                    child: Text('Vehicle issue'),
                  ),
                  DropdownMenuItem(
                    value: 'weather_or_route_issue',
                    child: Text('Weather or route issue'),
                  ),
                  DropdownMenuItem(value: 'other', child: Text('Other')),
                ],
                onChanged: (value) => setState(() => reason = value ?? reason),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: details,
                maxLines: 3,
                decoration: InputDecoration(
                  labelText: reason == 'other'
                      ? 'Details (required)'
                      : 'Details (optional)',
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () {
                if (reason == 'other' && details.text.trim().isEmpty) return;
                Navigator.pop(dialogContext, true);
              },
              child: const Text('Reschedule next day'),
            ),
          ],
        ),
      ),
    );
    if (submitted == true) {
      try {
        await controller.markDeliveryIncomplete(
          orderId,
          reason: reason,
          details: details.text,
        );
        if (context.mounted) {
          Navigator.pop(context);
        }
      } catch (_) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                controller.error ?? 'Unable to reschedule delivery.',
              ),
            ),
          );
        }
      }
    }
    details.dispose();
  }
}
