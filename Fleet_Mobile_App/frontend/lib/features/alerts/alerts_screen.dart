import 'package:flutter/material.dart';

import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/fleet_widgets.dart';

class AlertsScreen extends StatelessWidget {
  const AlertsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          children: [
            Text(
              'Driver alerts',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w900),
            ),
            const Spacer(),
            StatusPill(
              label: '${controller.activeAlertCount} active',
              color: AppColors.critical,
            ),
          ],
        ),
        const SizedBox(height: 12),
        if (controller.alerts.isEmpty)
          FleetCard(
            child: Text(
              controller.error ?? 'No active backend alerts for this driver.',
              style: const TextStyle(color: AppColors.muted),
            ),
          ),
        ...controller.alerts.map(
          (alert) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: FleetCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(
                        Icons.warning_amber_rounded,
                        color: severityColor(alert.severity),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          alert.title,
                          style: const TextStyle(fontWeight: FontWeight.w900),
                        ),
                      ),
                      StatusPill(
                        label: alert.category,
                        color: severityColor(alert.severity),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    alert.message,
                    style: const TextStyle(color: AppColors.muted),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Text(
                        alert.timestamp,
                        style: const TextStyle(
                          color: AppColors.muted,
                          fontSize: 12,
                        ),
                      ),
                      const Spacer(),
                      FleetButton(
                        label: alert.acknowledged ? 'Done' : 'Acknowledge',
                        filled: !alert.acknowledged,
                        onPressed: alert.acknowledged
                            ? null
                            : () async {
                                await controller.acknowledgeAlert(alert.id);
                                if (!context.mounted) {
                                  return;
                                }
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text(
                                      controller.error ?? 'Alert acknowledged',
                                    ),
                                  ),
                                );
                              },
                      ),
                    ],
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
