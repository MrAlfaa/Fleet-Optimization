import 'package:flutter/material.dart';

import '../core/routing/app_routes.dart';
import '../core/state/app_controller.dart';
import '../core/theme/app_theme.dart';
import '../features/auth/login_screen.dart';
import '../features/auth/register_screen.dart';
import '../features/auth/unlock_screen.dart';
import '../features/home/driver_shell.dart';
import '../features/issues/issue_report_screen.dart';

class FleetOptDriverApp extends StatefulWidget {
  const FleetOptDriverApp({super.key, required this.controller});

  final AppController controller;

  @override
  State<FleetOptDriverApp> createState() => _FleetOptDriverAppState();
}

class _FleetOptDriverAppState extends State<FleetOptDriverApp> with WidgetsBindingObserver {
  DateTime? _backgroundedAt;

  @override
  void initState() { super.initState(); WidgetsBinding.instance.addObserver(this); }
  @override
  void dispose() { WidgetsBinding.instance.removeObserver(this); super.dispose(); }
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused || state == AppLifecycleState.inactive) _backgroundedAt ??= DateTime.now();
    if (state == AppLifecycleState.resumed && _backgroundedAt != null) {
      if (DateTime.now().difference(_backgroundedAt!) >= const Duration(seconds: 60)) widget.controller.lockApp();
      _backgroundedAt = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppScope(
      controller: widget.controller,
      child: AnimatedBuilder(
        animation: widget.controller,
        builder: (context, _) {
          return MaterialApp(
            title: 'FleetOpt Driver',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.light(),
            home: widget.controller.isAuthenticated
                ? const DriverShell()
                : !widget.controller.enrolled
                    ? const LoginScreen()
                    : widget.controller.pinSetupRequired
                        ? const RegisterScreen()
                        : const UnlockScreen(),
            routes: {
              AppRoutes.login: (_) => const LoginScreen(),
              AppRoutes.register: (_) => const RegisterScreen(),
              AppRoutes.issueReport: (_) => const IssueReportScreen(),
            },
          );
        },
      ),
    );
  }
}

class AppScope extends InheritedWidget {
  const AppScope({super.key, required this.controller, required super.child});

  final AppController controller;

  static AppController of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<AppScope>();
    assert(scope != null, 'AppScope is missing from the widget tree');
    return scope!.controller;
  }

  @override
  bool updateShouldNotify(AppScope oldWidget) =>
      controller != oldWidget.controller;
}
