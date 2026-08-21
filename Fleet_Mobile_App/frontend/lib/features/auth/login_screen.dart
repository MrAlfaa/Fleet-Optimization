import 'package:flutter/material.dart';
import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/fleet_widgets.dart';
import 'auth_layout.dart';

class LoginScreen extends StatefulWidget { const LoginScreen({super.key}); @override State<LoginScreen> createState() => _LoginScreenState(); }
class _LoginScreenState extends State<LoginScreen> {
  final _username = TextEditingController(); final _password = TextEditingController(); bool _obscure = true;
  @override void dispose() { _username.dispose(); _password.dispose(); super.dispose(); }
  @override Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    return AuthLayout(title: 'Register this driver device', subtitle: 'Enter the username and one-time password provided by your fleet administrator.', footer: const SizedBox.shrink(), children: [
      TextField(controller: _username, textCapitalization: TextCapitalization.none, decoration: const InputDecoration(labelText: 'Driver username', prefixIcon: Icon(Icons.badge_outlined))),
      const SizedBox(height: 14),
      TextField(controller: _password, obscureText: _obscure, decoration: InputDecoration(labelText: 'Temporary password', prefixIcon: const Icon(Icons.lock_outline), suffixIcon: IconButton(onPressed: () => setState(() => _obscure = !_obscure), icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined)))),
      const SizedBox(height: 12),
      const Text('Only one phone can be registered. A lost or replaced phone must be reset by the fleet administrator.', style: TextStyle(color: AppColors.muted, height: 1.5)),
      if (controller.error != null) ...[const SizedBox(height: 10), Text(controller.error!, style: const TextStyle(color: AppColors.critical, fontWeight: FontWeight.w700))],
      const SizedBox(height: 18),
      FleetButton(label: controller.loading ? 'Registering device...' : 'Register device', icon: Icons.phone_android_rounded, onPressed: controller.loading ? null : () => controller.enroll(_username.text, _password.text)),
    ]);
  }
}
