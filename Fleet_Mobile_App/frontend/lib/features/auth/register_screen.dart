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
  final _name = TextEditingController(text: 'Marcus Johnson');
  final _email = TextEditingController(text: 'marcus@fleetopt.ai');
  final _invite = TextEditingController(text: 'FLEET-2026');
  final _password = TextEditingController(text: 'driver123');
  bool _obscure = true;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _invite.dispose();
    _password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    final strength = (_password.text.length / 12).clamp(0.2, 1.0);
    return AuthLayout(
      title: 'Driver registration',
      subtitle: 'Use your fleet invite code to activate the driver workspace.',
      footer: TextButton(
        onPressed: () {
          controller.clearError();
          Navigator.of(context).pop();
        },
        child: const Text('Already have access? Sign in'),
      ),
      children: [
        TextField(
          key: const Key('register-name'),
          controller: _name,
          decoration: const InputDecoration(
            labelText: 'Driver name',
            prefixIcon: Icon(Icons.person_outline),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _email,
          keyboardType: TextInputType.emailAddress,
          decoration: const InputDecoration(
            labelText: 'Email address',
            prefixIcon: Icon(Icons.mail_outline),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _invite,
          decoration: const InputDecoration(
            labelText: 'Organization / invite code',
            prefixIcon: Icon(Icons.badge_outlined),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          controller: _password,
          obscureText: _obscure,
          onChanged: (_) => setState(() {}),
          decoration: InputDecoration(
            labelText: 'Password',
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
        const SizedBox(height: 10),
        LinearProgressIndicator(
          value: strength,
          minHeight: 6,
          borderRadius: BorderRadius.circular(999),
          color: strength > 0.7 ? AppColors.success : AppColors.warning,
          backgroundColor: AppColors.border,
        ),
        const SizedBox(height: 8),
        const Text(
          'Use 8+ characters for a stronger local prototype password.',
          style: TextStyle(color: AppColors.muted, fontSize: 12),
        ),
        if (controller.error != null) ...[
          const SizedBox(height: 8),
          Text(
            controller.error!,
            style: const TextStyle(
              color: AppColors.critical,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
        const SizedBox(height: 16),
        FleetButton(
          label: controller.loading
              ? 'Creating account...'
              : 'Create driver account',
          icon: Icons.verified_user_outlined,
          onPressed: controller.loading
              ? null
              : () => controller.register(
                  name: _name.text,
                  email: _email.text.trim(),
                  inviteCode: _invite.text,
                  password: _password.text,
                ),
        ),
      ],
    );
  }
}
