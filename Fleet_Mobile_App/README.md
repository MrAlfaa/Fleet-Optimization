# FleetOpt AI Mobile App

This folder contains the Android driver-side workspace.

Current frontend phase:

- `frontend/` contains a runnable Flutter Android driver frontend prototype
- no mobile backend is implemented
- driver data, route stops, alerts, and session state are local mock services

Planned mobile app scope:

- driver login
- assigned vehicle details
- assigned route and stop list
- launch Google Maps navigation
- delivery status updates
- reroute alerts
- maintenance risk alerts
- weather warnings
- trip start/end
- issue report and emergency action

The mobile app should consume the same future backend API as the web dashboard.

Run the Flutter frontend from PowerShell:

```powershell
cd "E:\PROJECTS\Out Source Project\AI Driven Fleet Optimization Project\Fleet_Mobile_App\frontend"
flutter pub get
flutter run
```

Verify:

```powershell
flutter analyze
flutter test
flutter build apk --debug
```
