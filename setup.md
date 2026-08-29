# AI Driven Fleet Optimization - Setup Guide

This guide explains how to set up and run the project after downloading or cloning the source code from Git.

The project has three main runnable parts:

- FastAPI backend: `backend`
- React web dashboard: `Fleet_Web_App/frontend`
- Flutter Android driver app: `Fleet_Mobile_App/frontend`

The backend is the central API for both the web app and the mobile app. Do not create a separate backend for Android.

## 1. Required Software

Install these before running the project:

- Git
- Python 3.11 or 3.12 required for the backend
- Node.js 20 or newer
- npm
- Flutter SDK
- Android Studio
- Android SDK Platform Tools
- Android emulator or a physical Android phone
- MongoDB Atlas database URI

Check tools:

### PowerShell

```powershell
git --version
python --version
node --version
npm --version
flutter --version
adb version
```

Do not use Python 3.14 for the backend. The project depends on `scikit-learn==1.6.1` for ML artifact compatibility, and that version may try to build from source on Python 3.14 instead of installing a Windows wheel.

### Git Bash

```bash
git --version
python --version
node --version
npm --version
flutter --version
adb version
```

Run Flutter doctor:

### PowerShell

```powershell
flutter doctor
flutter doctor --android-licenses
```

### Git Bash

```bash
flutter doctor
flutter doctor --android-licenses
```

## 2. Clone the Project

Replace `<repository-url>` with your Git repository URL.

### PowerShell

```powershell
git clone <repository-url>
cd "AI Driven Fleet Optimization Project"
```

### Git Bash

```bash
git clone <repository-url>
cd "AI Driven Fleet Optimization Project"
```

If your folder path has spaces, keep the quotes in PowerShell. In Git Bash, quotes are also safe.

## 3. Backend Setup

Backend path:

```text
backend
```

### 3.1 Create Python Virtual Environment

### PowerShell

```powershell
cd "backend"
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### Git Bash

```bash
cd backend
python -m venv venv
source venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Important for Git Bash: use `cd ..`, not `cd..`.

### 3.2 Create Backend Environment File

Copy the example env file:

### PowerShell

```powershell
Copy-Item .env.example .env
notepad .env
```

### Git Bash

```bash
cp .env.example .env
notepad .env
```

Edit `backend/.env` and set your own values:

```env
APP_NAME=AI Driven Fleet Optimization API
APP_VERSION=1.0.0
ENVIRONMENT=development
API_PREFIX=/api
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster-url>/
MONGODB_DB_NAME=fleet_optimization
JWT_SECRET_KEY=replace-with-your-own-strong-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
OSRM_BASE_URL=https://router.project-osrm.org
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:3000
```

Do not commit real MongoDB credentials or JWT secrets.

### 3.3 Seed Demo Data

Run seed scripts after configuring MongoDB Atlas.

### PowerShell

```powershell
python scripts\seed_users.py
python scripts\seed_fleet_data.py
python scripts\seed_ev_csv_fleet_data.py
python scripts\seed_driver_route_demo.py
```

Optional demand import and route data can be tested later through Swagger after login.

To populate an admin-only test environment without creating any driver or additional user, run:

```powershell
.\.venv\Scripts\python.exe scripts\seed_system_test_data.py
```

This creates unassigned fleet, maintenance, prediction, demand, delivery, and alert data. Create the driver yourself through the web Driver Management page before testing dispatch and the Android workflow.

### Git Bash

```bash
python scripts/seed_users.py
python scripts/seed_fleet_data.py
python scripts/seed_ev_csv_fleet_data.py
python scripts/seed_driver_route_demo.py
```

Admin-only system test data without a generated driver:

```bash
./.venv/Scripts/python.exe scripts/seed_system_test_data.py
```

### 3.4 Run Backend

Run backend on `0.0.0.0` so Android devices can reach it if needed.

### PowerShell

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Git Bash

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:

- Health: `http://127.0.0.1:8000/api/health`
- DB health: `http://127.0.0.1:8000/api/health/db`
- Swagger API docs: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Demo users:

```text
admin@fleet.local / Admin@12345
fleet.manager@fleet.local / Fleet@12345
maintenance.manager@fleet.local / Maint@12345
route.planner@fleet.local / Route@12345
driver@fleet.local / Driver@12345
```

## 4. Web App Setup

Web frontend path:

```text
Fleet_Web_App/frontend
```

The React web app is backend-connected and uses Google Maps for live-trip and route-planning views when a Maps browser key is configured.

### 4.1 Install Dependencies

Open a new terminal.

### PowerShell

```powershell
cd "Fleet_Web_App\frontend"
npm.cmd install
```

### Git Bash

```bash
cd Fleet_Web_App/frontend
npm install
```

### 4.2 Configure Web Environment

Copy the example file and set backend and Maps values.

### PowerShell

```powershell
Copy-Item .env.example .env
notepad .env
```

### Git Bash

```bash
cp .env.example .env
notepad .env
```

Use this shape:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

Operational maps use OpenStreetMap tiles and backend OSRM route geometry; no browser map key is required.

### 4.3 Run Web App

Use port `5174` to match the current local browser URL. If you prefer Vite default, use port `5173`.

### PowerShell

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5174
```

### Git Bash

```bash
npm run dev -- --host 127.0.0.1 --port 5174
```

Open:

```text
http://127.0.0.1:5174
```

### 4.4 Web App Checks

### PowerShell

```powershell
npm.cmd run build
npm.cmd run test
npm.cmd run lint
```

### Git Bash

```bash
npm run build
npm run test
npm run lint
```

## 5. Flutter Android App Setup

Flutter app path:

```text
Fleet_Mobile_App/frontend
```

The Flutter Android driver app is backend-connected for login, assigned route, assigned vehicle, alerts, delivery status, issue reporting, and foreground trip tracking. Google Maps is opened externally for stop and full-route navigation.

### 5.1 Install Flutter Dependencies

Open a new terminal.

### PowerShell

```powershell
cd "Fleet_Mobile_App\frontend"
flutter pub get
```

### Git Bash

```bash
cd Fleet_Mobile_App/frontend
flutter pub get
```

### 5.2 Check Available Devices

### PowerShell

```powershell
flutter devices
adb devices
```

### Git Bash

```bash
flutter devices
adb devices
```

## 6. Run Android App on Emulator

Start an emulator from Android Studio, or use Flutter CLI.

List emulators:

### PowerShell

```powershell
flutter emulators
```

### Git Bash

```bash
flutter emulators
```

Launch an emulator. Replace `<emulator_id>` with your emulator ID.

### PowerShell

```powershell
flutter emulators --launch <emulator_id>
flutter devices
flutter run -d <emulator_device_id> --dart-define=FLEETOPT_API_BASE_URL=http://10.0.2.2:8000/api
```

### Git Bash

```bash
flutter emulators --launch <emulator_id>
flutter devices
flutter run -d <emulator_device_id> --dart-define=FLEETOPT_API_BASE_URL=http://10.0.2.2:8000/api
```

If multiple devices are connected:

### PowerShell

```powershell
flutter run -d <device_id>
```

### Git Bash

```bash
flutter run -d <device_id>
```

For Android emulator backend access later, use:

```text
http://10.0.2.2:8000/api
```

## 7. Run Android App on Physical Device

Enable these on your Android phone:

- Developer Options
- USB Debugging

Connect the phone by USB and check:

### PowerShell

```powershell
adb devices
flutter devices
```

### Git Bash

```bash
adb devices
flutter devices
```

Run the app:

### PowerShell

```powershell
flutter run -d <device_id>
```

### Git Bash

```bash
flutter run -d <device_id>
```

For backend-connected mobile testing over USB, reverse the backend port. If the connected phone is `R58R85Q2HWH`, keep the device id explicit:

### PowerShell

```powershell
adb -s R58R85Q2HWH reverse tcp:8000 tcp:8000
flutter run -d R58R85Q2HWH --dart-define=FLEETOPT_API_BASE_URL=http://127.0.0.1:8000/api
```

### Git Bash

```bash
adb -s R58R85Q2HWH reverse tcp:8000 tcp:8000
flutter run -d R58R85Q2HWH --dart-define=FLEETOPT_API_BASE_URL=http://127.0.0.1:8000/api
```

Then the Android app can use:

```text
http://127.0.0.1:8000/api
```

If USB reverse does not work, run backend with `--host 0.0.0.0`, find your computer LAN IP, and use:

```text
http://<your-computer-lan-ip>:8000/api
```

## 8. Build Android APK

### PowerShell

```powershell
cd "Fleet_Mobile_App\frontend"
flutter build apk --debug
```

### Git Bash

```bash
cd Fleet_Mobile_App/frontend
flutter build apk --debug
```

APK output:

```text
Fleet_Mobile_App/frontend/build/app/outputs/flutter-apk/app-debug.apk
```

Install APK manually:

### PowerShell

```powershell
adb install -r "build\app\outputs\flutter-apk\app-debug.apk"
```

### Git Bash

```bash
adb install -r build/app/outputs/flutter-apk/app-debug.apk
```

## 9. Flutter Checks

### PowerShell

```powershell
flutter analyze
flutter test
flutter build apk --debug
```

### Git Bash

```bash
flutter analyze
flutter test
flutter build apk --debug
```

## 10. Recommended Run Order

Use three terminals.

Terminal 1 - backend:

```powershell
cd "backend"
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 - web app:

```powershell
cd "Fleet_Web_App\frontend"
npm.cmd run dev -- --host 127.0.0.1 --port 5174
```

Terminal 3 - Android app:

```powershell
cd "Fleet_Mobile_App\frontend"
flutter run
```

Git Bash equivalent:

```bash
cd backend
source venv/Scripts/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```bash
cd Fleet_Web_App/frontend
npm run dev -- --host 127.0.0.1 --port 5174
```

```bash
cd Fleet_Mobile_App/frontend
flutter run
```

## 11. Common Problems

### PowerShell blocks venv activation

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

### `scikit-learn` fails with Meson/compiler error

If install fails at `scikit-learn==1.6.1` with an error like:

```text
ERROR: Unknown compiler(s)
Preparing metadata (pyproject.toml) did not run successfully
```

check Python version:

```powershell
python --version
```

If it shows Python `3.14.x`, install Python 3.11 or 3.12, delete the old virtual environment, and recreate it.

PowerShell:

```powershell
cd "backend"
deactivate
Remove-Item -Recurse -Force venv
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Git Bash:

```bash
cd backend
deactivate 2>/dev/null || true
rm -rf venv
py -3.12 -m venv venv
source venv/Scripts/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

If `py -3.12` is not found, install Python 3.12 from `https://www.python.org/downloads/windows/` and tick **Add python.exe to PATH** during installation.

### Git Bash says `cd..: command not found`

Use:

```bash
cd ..
```

not:

```bash
cd..
```

### Android device not listed

```powershell
adb kill-server
adb start-server
adb devices
flutter devices
```

Git Bash:

```bash
adb kill-server
adb start-server
adb devices
flutter devices
```

### Backend cannot connect to MongoDB

Check:

- `backend/.env` exists
- `MONGODB_URI` is correct
- MongoDB Atlas network access allows your IP
- database user/password are correct

Run:

```powershell
python scripts\seed_users.py
```

or:

```bash
python scripts/seed_users.py
```

### Web app port already used

Use another port:

```powershell
npm.cmd run dev -- --host 127.0.0.1 --port 5175
```

```bash
npm run dev -- --host 127.0.0.1 --port 5175
```

## 12. Current Phase Notes

- Backend has authentication, fleet data APIs, predictive maintenance APIs, demand forecasting APIs, route prediction APIs, delivery APIs, and route optimization APIs.
- React web and Flutter driver clients use the central FastAPI backend.
- Driver accounts must be created by an administrator from **Driver Management**.
- On first mobile launch, enter the administrator-provided username and temporary password, then configure a six-digit PIN and optional biometrics.
- A driver can enroll only one phone. Lost, replaced, or reset phones require an administrator device reset and a new temporary password.
- Mobile tokens, device secrets, and PIN hashes are stored using Android secure storage, not SharedPreferences.
