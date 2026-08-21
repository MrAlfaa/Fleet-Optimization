import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/theme/app_theme.dart';
import '../../models/driver_models.dart';

Future<PreTripInspection?> showPreTripInspectionSheet(
  BuildContext context, {
  required double initialMileage,
}) {
  return showModalBottomSheet<PreTripInspection>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: Colors.transparent,
    builder: (_) => _PreTripInspectionSheet(initialMileage: initialMileage),
  );
}

Future<PostTripInspection?> showPostTripInspectionSheet(
  BuildContext context, {
  required double initialMileage,
}) {
  return showModalBottomSheet<PostTripInspection>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    backgroundColor: Colors.transparent,
    builder: (_) => _PostTripInspectionSheet(initialMileage: initialMileage),
  );
}

const _tireOptions = {
  'normal': 'Normal - no visible concern',
  'worn': 'Worn - monitor condition',
  'damaged': 'Damaged - inspection required',
};
const _brakeOptions = {
  'normal': 'Normal response',
  'noisy': 'Unusual brake noise',
  'reduced_response': 'Reduced braking response',
  'warning_light': 'Brake warning light',
};
const _chargingOptions = {
  'normal': 'Charging normally',
  'intermittent': 'Intermittent charging',
  'not_charging': 'Not charging',
  'port_damaged': 'Charging port damaged',
};
const _damageOptions = {
  'none': 'No visible damage',
  'minor': 'Minor visible damage',
  'major': 'Major damage',
};
const _warningOptions = {
  'none': 'No dashboard warning',
  'amber': 'Amber warning',
  'red': 'Red critical warning',
};
const _observationOptions = {
  'none': 'None',
  'mild': 'Mild',
  'severe': 'Severe',
};
const _changeOptions = {
  'none': 'No change',
  'minor': 'Minor change',
  'significant': 'Significant change',
};
const _chargingProblemOptions = {
  'none': 'No charging problem',
  'intermittent': 'Intermittent problem',
  'failed': 'Charging failed',
};

class _SheetFrame extends StatelessWidget {
  const _SheetFrame({
    required this.title,
    required this.subtitle,
    required this.formKey,
    required this.onSubmit,
    required this.children,
  });

  final String title;
  final String subtitle;
  final GlobalKey<FormState> formKey;
  final VoidCallback onSubmit;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.sizeOf(context).height * 0.92,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Column(
        children: [
          Container(
            width: 44,
            height: 4,
            margin: const EdgeInsets.only(top: 10),
            decoration: BoxDecoration(
              color: const Color(0xFFD4DCE8),
              borderRadius: BorderRadius.circular(99),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 14),
            child: Row(
              children: [
                Container(
                  width: 46,
                  height: 46,
                  decoration: BoxDecoration(
                    color: AppColors.primary.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(
                    Icons.fact_check_outlined,
                    color: AppColors.primary,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        subtitle,
                        style: const TextStyle(
                          color: AppColors.muted,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: Form(
              key: formKey,
              child: ListView(
                padding: EdgeInsets.fromLTRB(
                  20,
                  18,
                  20,
                  MediaQuery.viewInsetsOf(context).bottom + 24,
                ),
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF4F7FB),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Text(
                      'Select the closest observation. Critical selections may block this vehicle and notify the fleet manager.',
                      style: TextStyle(
                        color: AppColors.muted,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  ...children,
                  const SizedBox(height: 18),
                  FilledButton.icon(
                    onPressed: onSubmit,
                    icon: const Icon(Icons.verified_outlined),
                    label: const Padding(
                      padding: EdgeInsets.symmetric(vertical: 14),
                      child: Text(
                        'Submit inspection',
                        style: TextStyle(fontWeight: FontWeight.w800),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PreTripInspectionSheet extends StatefulWidget {
  const _PreTripInspectionSheet({required this.initialMileage});
  final double initialMileage;

  @override
  State<_PreTripInspectionSheet> createState() =>
      _PreTripInspectionSheetState();
}

class _PreTripInspectionSheetState extends State<_PreTripInspectionSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _odometer;
  final _soc = TextEditingController(text: '80');
  final _notes = TextEditingController();
  String tire = 'normal',
      brake = 'normal',
      charging = 'normal',
      damage = 'none';
  String warning = 'none', noise = 'none', vibration = 'none';

  @override
  void initState() {
    super.initState();
    _odometer = TextEditingController(
      text: widget.initialMileage.toStringAsFixed(0),
    );
  }

  @override
  void dispose() {
    _odometer.dispose();
    _soc.dispose();
    _notes.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return _SheetFrame(
      title: 'Pre-trip vehicle check',
      subtitle: 'Required before starting the assigned delivery route',
      formKey: _formKey,
      onSubmit: _submit,
      children: [
        _numberField(
          _odometer,
          'Starting odometer (km)',
          min: widget.initialMileage,
        ),
        _numberField(_soc, 'Battery charge - SoC (%)', min: 0, max: 100),
        _dropdown(
          'Tire condition',
          tire,
          _tireOptions,
          (value) => setState(() => tire = value),
        ),
        _dropdown(
          'Brake condition',
          brake,
          _brakeOptions,
          (value) => setState(() => brake = value),
        ),
        _dropdown(
          'Charging system',
          charging,
          _chargingOptions,
          (value) => setState(() => charging = value),
        ),
        _dropdown(
          'Visible vehicle damage',
          damage,
          _damageOptions,
          (value) => setState(() => damage = value),
        ),
        _dropdown(
          'Dashboard warning',
          warning,
          _warningOptions,
          (value) => setState(() => warning = value),
        ),
        _dropdown(
          'Unusual noise',
          noise,
          _observationOptions,
          (value) => setState(() => noise = value),
        ),
        _dropdown(
          'Unusual vibration',
          vibration,
          _observationOptions,
          (value) => setState(() => vibration = value),
        ),
        _notesField(_notes),
      ],
    );
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.pop(
      context,
      PreTripInspection(
        odometer: double.parse(_odometer.text),
        batterySoc: double.parse(_soc.text),
        tireCondition: tire,
        brakeCondition: brake,
        chargingCondition: charging,
        vehicleDamage: damage,
        dashboardWarning: warning,
        unusualNoise: noise,
        unusualVibration: vibration,
        notes: _notes.text,
      ),
    );
  }
}

class _PostTripInspectionSheet extends StatefulWidget {
  const _PostTripInspectionSheet({required this.initialMileage});
  final double initialMileage;

  @override
  State<_PostTripInspectionSheet> createState() =>
      _PostTripInspectionSheetState();
}

class _PostTripInspectionSheetState extends State<_PostTripInspectionSheet> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _odometer;
  final _soc = TextEditingController(text: '50');
  final _notes = TextEditingController();
  String tire = 'none', brake = 'none', charging = 'none', damage = 'none';
  String warning = 'none', noise = 'none', vibration = 'none';

  @override
  void initState() {
    super.initState();
    _odometer = TextEditingController(
      text: widget.initialMileage.toStringAsFixed(0),
    );
  }

  @override
  void dispose() {
    _odometer.dispose();
    _soc.dispose();
    _notes.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return _SheetFrame(
      title: 'Post-trip vehicle check',
      subtitle: 'Record the vehicle condition before closing this route',
      formKey: _formKey,
      onSubmit: _submit,
      children: [
        _numberField(
          _odometer,
          'Ending odometer (km)',
          min: widget.initialMileage,
        ),
        _numberField(_soc, 'Ending battery charge - SoC (%)', min: 0, max: 100),
        _dropdown(
          'Tire condition changed?',
          tire,
          _changeOptions,
          (value) => setState(() => tire = value),
        ),
        _dropdown(
          'Brake condition changed?',
          brake,
          _changeOptions,
          (value) => setState(() => brake = value),
        ),
        _dropdown(
          'Charging problem?',
          charging,
          _chargingProblemOptions,
          (value) => setState(() => charging = value),
        ),
        _dropdown(
          'Vehicle damage?',
          damage,
          _damageOptions,
          (value) => setState(() => damage = value),
        ),
        _dropdown(
          'New dashboard warning',
          warning,
          _warningOptions,
          (value) => setState(() => warning = value),
        ),
        _dropdown(
          'Unusual noise',
          noise,
          _observationOptions,
          (value) => setState(() => noise = value),
        ),
        _dropdown(
          'Unusual vibration',
          vibration,
          _observationOptions,
          (value) => setState(() => vibration = value),
        ),
        _notesField(_notes),
      ],
    );
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.pop(
      context,
      PostTripInspection(
        endingOdometer: double.parse(_odometer.text),
        endingBatterySoc: double.parse(_soc.text),
        tireConditionChange: tire,
        brakeConditionChange: brake,
        chargingProblem: charging,
        vehicleDamage: damage,
        dashboardWarning: warning,
        unusualNoise: noise,
        unusualVibration: vibration,
        notes: _notes.text,
      ),
    );
  }
}

Widget _numberField(
  TextEditingController controller,
  String label, {
  required double min,
  double? max,
}) {
  return Padding(
    padding: const EdgeInsets.only(bottom: 13),
    child: TextFormField(
      controller: controller,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      inputFormatters: [FilteringTextInputFormatter.allow(RegExp(r'[0-9.]'))],
      decoration: InputDecoration(labelText: label),
      validator: (value) {
        final number = double.tryParse(value ?? '');
        if (number == null) {
          return 'Enter a valid number';
        }
        if (number < min) {
          return 'Value cannot be below ${min.toStringAsFixed(0)}';
        }
        if (max != null && number > max) {
          return 'Value cannot exceed ${max.toStringAsFixed(0)}';
        }
        return null;
      },
    ),
  );
}

Widget _dropdown(
  String label,
  String value,
  Map<String, String> options,
  ValueChanged<String> onChanged,
) {
  return Padding(
    padding: const EdgeInsets.only(bottom: 13),
    child: DropdownButtonFormField<String>(
      initialValue: value,
      isExpanded: true,
      decoration: InputDecoration(labelText: label),
      items: options.entries
          .map(
            (entry) =>
                DropdownMenuItem(value: entry.key, child: Text(entry.value)),
          )
          .toList(),
      onChanged: (next) {
        if (next != null) onChanged(next);
      },
    ),
  );
}

Widget _notesField(TextEditingController controller) {
  return TextFormField(
    controller: controller,
    maxLines: 3,
    maxLength: 1000,
    decoration: const InputDecoration(
      labelText: 'Additional notes (optional)',
      alignLabelWithHint: true,
    ),
  );
}
