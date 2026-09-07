import 'package:flutter/material.dart';
import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/fleet_widgets.dart';
import 'auth_layout.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});
  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _pin = TextEditingController();
  final _confirm = TextEditingController();
  bool _biometrics = false;
  bool _supported = false;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final value = await AppScope.of(context).canUseBiometrics();
      if (mounted) setState(() => _supported = value);
    });
  }

  @override
  void dispose() {
    _pin.dispose();
    _confirm.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    return AuthLayout(
      title: 'Secure this device',
      subtitle:
          'Create a six-digit PIN. The PIN and biometric data never leave this phone.',
      footer: const SizedBox.shrink(),
      children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppColors.success.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(12),
          ),
          child: const Row(
            children: [
              Icon(
                Icons.check_circle_outline_rounded,
                color: AppColors.success,
              ),
              SizedBox(width: 10),
              Expanded(
                child: Text(
                  'Device verified successfully. Create your PIN to finish registration.',
                  style: TextStyle(fontWeight: FontWeight.w700, height: 1.35),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _pin,
          obscureText: true,
          keyboardType: TextInputType.number,
          maxLength: 6,
          decoration: const InputDecoration(
            labelText: 'Six-digit PIN',
            prefixIcon: Icon(Icons.pin_outlined),
          ),
        ),
        const SizedBox(height: 10),
        TextField(
          controller: _confirm,
          obscureText: true,
          keyboardType: TextInputType.number,
          maxLength: 6,
          decoration: const InputDecoration(
            labelText: 'Confirm PIN',
            prefixIcon: Icon(Icons.verified_user_outlined),
          ),
        ),
        if (_supported)
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            value: _biometrics,
            onChanged: (value) => setState(() => _biometrics = value),
            title: const Text(
              'Enable biometric unlock',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            subtitle: const Text('PIN remains available as fallback.'),
          ),
        if (controller.error != null)
          Text(
            controller.error!,
            style: const TextStyle(
              color: AppColors.critical,
              fontWeight: FontWeight.w700,
            ),
          ),
        const SizedBox(height: 14),
        FleetButton(
          label: controller.loading
              ? 'Preparing driver workspace...'
              : 'Complete secure registration',
          icon: Icons.shield_outlined,
          loading: controller.loading,
          onPressed: () async {
            if (_pin.text != _confirm.text) {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('PIN values do not match.')),
              );
              return;
            }
            await controller.configurePin(
              _pin.text,
              enableBiometrics: _biometrics,
            );
          },
        ),
      ],
    );
  }
}
