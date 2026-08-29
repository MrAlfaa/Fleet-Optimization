import 'package:flutter/material.dart';

import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/fleet_widgets.dart';

class VehicleScreen extends StatelessWidget {
  const VehicleScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    final vehicle = controller.vehicle;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        FleetCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.local_shipping_rounded,
                    color: AppColors.primary,
                    size: 34,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          vehicle.number,
                          style: Theme.of(context).textTheme.headlineSmall
                              ?.copyWith(fontWeight: FontWeight.w900),
                        ),
                        Text(
                          '${vehicle.model} - ${vehicle.category.replaceAll('_', ' ')}',
                          style: const TextStyle(color: AppColors.muted),
                        ),
                      ],
                    ),
                  ),
                  StatusPill(
                    label: vehicle.riskLevel.toUpperCase(),
                    color: AppColors.warning,
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Row(
                children: [
                  MetricTile(
                    label: 'Mileage',
                    value: '${vehicle.mileage}',
                    icon: Icons.speed_rounded,
                  ),
                  const SizedBox(width: 10),
                  MetricTile(
                    label: 'Powertrain',
                    value: vehicle.fuelType,
                    icon: Icons.settings_input_component_outlined,
                    color: AppColors.primary,
                  ),
                ],
              ),
              const SizedBox(height: 16),
              StatusPill(label: vehicle.modelStatus, color: AppColors.primary),
              const SizedBox(height: 10),
              Text(
                vehicle.riskSummary,
                style: const TextStyle(color: AppColors.muted),
              ),
            ],
          ),
        ),
        const SizedBox(height: 14),
        Text(
          'Pre-trip inspection',
          style: Theme.of(
            context,
          ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 10),
        const _InspectionTile(
          label: 'Brake condition',
          state: 'Required',
          color: AppColors.primary,
        ),
        const _InspectionTile(
          label: 'Tires and visible damage',
          state: 'Required',
          color: AppColors.primary,
        ),
        _InspectionTile(
          label: vehicle.powertrainConditionLabel,
          state: 'Required',
          color: AppColors.primary,
        ),
        _InspectionTile(
          label: vehicle.energyIssueLabel,
          state: 'Required',
          color: AppColors.primary,
        ),
        if (vehicle.supportsBatteryContext)
          const _InspectionTile(
            label: 'Battery charge (operational context)',
            state: 'Optional',
            color: AppColors.muted,
          ),
      ],
    );
  }
}

class _InspectionTile extends StatelessWidget {
  const _InspectionTile({
    required this.label,
    required this.state,
    required this.color,
  });

  final String label;
  final String state;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: FleetCard(
        child: Row(
          children: [
            Icon(Icons.check_circle_outline, color: color),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                label,
                style: const TextStyle(fontWeight: FontWeight.w800),
              ),
            ),
            StatusPill(label: state, color: color),
          ],
        ),
      ),
    );
  }
}
