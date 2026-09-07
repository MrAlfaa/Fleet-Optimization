import 'package:flutter/material.dart';
import '../../app/fleetopt_driver_app.dart';
import '../../core/state/app_controller.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/fleet_widgets.dart';
import 'auth_layout.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _username = TextEditingController();
  final _password = TextEditingController();
  bool _obscure = true;
  @override
  void dispose() {
    _username.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit(AppController controller) async {
    FocusScope.of(context).unfocus();
    if (_username.text.trim().isEmpty || _password.text.isEmpty) {
      await _showError('Enter the driver username and temporary password.');
      return;
    }
    await controller.enroll(_username.text.trim(), _password.text);
    if (mounted && controller.error != null) {
      await _showError(controller.error!);
    }
  }

  Future<void> _showError(String message) => showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      icon: const Icon(
        Icons.error_outline_rounded,
        color: AppColors.critical,
        size: 36,
      ),
      title: const Text('Registration could not be completed'),
      content: Text(message, textAlign: TextAlign.center),
      actionsAlignment: MainAxisAlignment.center,
      actions: [
        FilledButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Try again'),
        ),
      ],
    ),
  );

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    return AuthLayout(
      title: 'Register this driver device',
      subtitle:
          'Enter the username and one-time password provided by your fleet administrator.',
      footer: const SizedBox.shrink(),
      children: [
        TextField(
          controller: _username,
          textCapitalization: TextCapitalization.none,
          decoration: const InputDecoration(
            labelText: 'Driver username',
            prefixIcon: Icon(Icons.badge_outlined),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _password,
          obscureText: _obscure,
          decoration: InputDecoration(
            labelText: 'Temporary password',
            prefixIcon: const Icon(Icons.lock_outline),
            suffixIcon: IconButton(
              onPressed: () => setState(() => _obscure = !_obscure),
              icon: Icon(
                _obscure
                    ? Icons.visibility_outlined
                    : Icons.visibility_off_outlined,
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          'Only one phone can be registered. A lost or replaced phone must be reset by the fleet administrator.',
          style: TextStyle(color: AppColors.muted, height: 1.5),
        ),
        const SizedBox(height: 18),
        FleetButton(
          label: controller.loading ? 'Verifying device...' : 'Register device',
          icon: Icons.phone_android_rounded,
          loading: controller.loading,
          onPressed: () => _submit(controller),
        ),
      ],
    );
  }
}
