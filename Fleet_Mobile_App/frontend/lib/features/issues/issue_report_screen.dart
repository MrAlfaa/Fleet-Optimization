import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';
import '../../widgets/fleet_widgets.dart';

class IssueReportScreen extends StatefulWidget {
  const IssueReportScreen({super.key});

  @override
  State<IssueReportScreen> createState() => _IssueReportScreenState();
}

class _IssueReportScreenState extends State<IssueReportScreen> {
  String _severity = 'Route issue';
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
                  'This frontend stores the report locally only. Backend alert sync is a later phase.',
                  style: TextStyle(color: AppColors.muted),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  initialValue: _severity,
                  decoration: const InputDecoration(labelText: 'Issue type'),
                  items: const [
                    DropdownMenuItem(
                      value: 'Route issue',
                      child: Text('Route issue'),
                    ),
                    DropdownMenuItem(
                      value: 'Vehicle issue',
                      child: Text('Vehicle issue'),
                    ),
                    DropdownMenuItem(
                      value: 'Customer unavailable',
                      child: Text('Customer unavailable'),
                    ),
                    DropdownMenuItem(
                      value: 'Emergency',
                      child: Text('Emergency'),
                    ),
                  ],
                  onChanged: (value) =>
                      setState(() => _severity = value ?? _severity),
                ),
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
                  label: _severity == 'Emergency'
                      ? 'Send emergency report'
                      : 'Submit report',
                  icon: Icons.send_rounded,
                  danger: _severity == 'Emergency',
                  onPressed: () {
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text('Mock report captured: $_severity'),
                      ),
                    );
                    Navigator.of(context).pop();
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
