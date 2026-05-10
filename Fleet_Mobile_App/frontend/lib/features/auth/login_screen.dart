import 'package:flutter/material.dart';

import '../../app/fleetopt_driver_app.dart';
import '../../core/routing/app_routes.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/fleet_widgets.dart';
import 'auth_layout.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController(text: 'driver@fleetopt.ai');
  final _password = TextEditingController(text: 'driver123');
  bool _remember = true;
  bool _obscure = true;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    return AuthLayout(
      title: 'Driver sign in',
      subtitle:
          'Access assigned route, vehicle risk alerts, and delivery stops.',
      footer: TextButton(
        onPressed: () {
          controller.clearError();
          Navigator.of(context).pushNamed(AppRoutes.register);
        },
        child: const Text('New driver? Create account with invite code'),
      ),
      children: [
        TextField(
          key: const Key('login-email'),
          controller: _email,
          keyboardType: TextInputType.emailAddress,
          decoration: const InputDecoration(
            labelText: 'Email address',
            prefixIcon: Icon(Icons.mail_outline),
          ),
        ),
        const SizedBox(height: 14),
        TextField(
          key: const Key('login-password'),
          controller: _password,
          obscureText: _obscure,
          decoration: InputDecoration(
            labelText: 'Password',
            prefixIcon: const Icon(Icons.lock_outline),
            suffixIcon: IconButton(
              tooltip: _obscure ? 'Show password' : 'Hide password',
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
        Row(
          children: [
            Checkbox(
              value: _remember,
              onChanged: (value) => setState(() => _remember = value ?? true),
            ),
            const Text('Remember this device'),
          ],
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
          label: controller.loading ? 'Signing in...' : 'Sign in',
          icon: Icons.arrow_forward_rounded,
          onPressed: controller.loading
              ? null
              : () => controller.login(_email.text.trim(), _password.text),
        ),
      ],
    );
  }
}
