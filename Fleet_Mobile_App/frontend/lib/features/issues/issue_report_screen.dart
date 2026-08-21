import 'package:flutter/material.dart';

import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/fleet_widgets.dart';

class IssueReportScreen extends StatefulWidget {
  const IssueReportScreen({super.key});

  @override
  State<IssueReportScreen> createState() => _IssueReportScreenState();
}

class _IssueReportScreenState extends State<IssueReportScreen> {
  String _severity = 'warning';
  String _category = 'battery';
  final _notes = TextEditingController();

  @override
  void dispose() {
    _notes.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Report issue')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          FleetCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Emergency / issue report',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Issue reports are sent to the backend and converted into driver alerts for fleet staff review.',
                  style: TextStyle(color: AppColors.muted),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  initialValue: _category,
                  decoration: const InputDecoration(labelText: 'Vehicle system'),
                  items: const [
                    DropdownMenuItem(value: 'battery', child: Text('Battery')),
                    DropdownMenuItem(value: 'brakes', child: Text('Brakes')),
                    DropdownMenuItem(value: 'tires', child: Text('Tires')),
                    DropdownMenuItem(value: 'motor_drivetrain', child: Text('Motor / drivetrain')),
                    DropdownMenuItem(value: 'charging', child: Text('Charging')),
                    DropdownMenuItem(value: 'suspension', child: Text('Suspension')),
                    DropdownMenuItem(value: 'thermal_system', child: Text('Thermal system')),
                    DropdownMenuItem(value: 'other', child: Text('Other')),
                  ],
                  onChanged: (value) =>
                      setState(() => _category = value ?? _category),
                ),
                const SizedBox(height: 14),
                DropdownButtonFormField<String>(initialValue: _severity, decoration: const InputDecoration(labelText: 'Severity'), items: const [DropdownMenuItem(value: 'info', child: Text('Low')), DropdownMenuItem(value: 'warning', child: Text('Warning')), DropdownMenuItem(value: 'critical', child: Text('Critical'))], onChanged: (value) => setState(() => _severity = value ?? _severity)),
                const SizedBox(height: 14),
                TextField(
                  controller: _notes,
                  minLines: 4,
                  maxLines: 6,
                  decoration: const InputDecoration(
                    labelText: 'Notes',
                    hintText: 'Describe the road, vehicle, or delivery issue.',
                    alignLabelWithHint: true,
                  ),
                ),
                const SizedBox(height: 16),
                FleetButton(
                  label: _severity == 'critical'
                      ? 'Send emergency report'
                      : 'Submit report',
                  icon: Icons.send_rounded,
                  danger: _severity == 'critical',
                  onPressed: () async {
                    final controller = AppScope.of(context);
                    final notes = _notes.text.trim();
                    if (notes.isEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Enter issue notes before submitting.'),
                        ),
                      );
                      return;
                    }
                    try {
                      await controller.submitIssue(
                        title: '${_category.replaceAll('_', ' ')} issue',
                        message: notes,
                        severity: _severity,
                        category: _category,
                      );
                      if (!context.mounted) {
                        return;
                      }
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('Issue report sent.')),
                      );
                      Navigator.of(context).pop();
                    } catch (_) {
                      if (!context.mounted) {
                        return;
                      }
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(
                            controller.error ?? 'Unable to send issue report.',
                          ),
                        ),
                      );
                    }
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
