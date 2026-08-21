import 'package:flutter/material.dart';
import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/fleet_widgets.dart';
import 'auth_layout.dart';

class UnlockScreen extends StatefulWidget { const UnlockScreen({super.key}); @override State<UnlockScreen> createState() => _UnlockScreenState(); }
class _UnlockScreenState extends State<UnlockScreen> {
  final _pin = TextEditingController(); bool _supported = false;
  @override void initState() { super.initState(); WidgetsBinding.instance.addPostFrameCallback((_) async { final value = await AppScope.of(context).canUseBiometrics(); if (mounted) setState(() => _supported = value); }); }
  @override void dispose() { _pin.dispose(); super.dispose(); }
  @override Widget build(BuildContext context) { final controller = AppScope.of(context); return AuthLayout(title: 'Unlock FleetOpt Driver', subtitle: 'Authenticate locally to load your current route and delivery work.', footer: const SizedBox.shrink(), children: [
    if (_supported) ...[FleetButton(label: 'Unlock with biometrics', icon: Icons.fingerprint_rounded, onPressed: controller.loading ? null : controller.unlockWithBiometrics), const SizedBox(height: 18)],
    TextField(controller: _pin, obscureText: true, maxLength: 6, keyboardType: TextInputType.number, decoration: const InputDecoration(labelText: 'Six-digit PIN', prefixIcon: Icon(Icons.pin_outlined))),
    if (controller.error != null) Text(controller.error!, style: const TextStyle(color: AppColors.critical, fontWeight: FontWeight.w700)),
    const SizedBox(height: 14), FleetButton(label: controller.loading ? 'Unlocking...' : 'Unlock with PIN', icon: Icons.lock_open_rounded, onPressed: controller.loading ? null : () => controller.unlockWithPin(_pin.text)),
    const SizedBox(height: 10), TextButton(onPressed: controller.forgetDevice, child: const Text('Device was reset by administrator')),
  ]); }
}
