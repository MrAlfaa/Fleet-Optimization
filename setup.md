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
- Python 3.11 or 3.12 recommended
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
```

Optional demand import and route data can be tested later through Swagger after login.

### Git Bash

```bash
python scripts/seed_users.py
python scripts/seed_fleet_data.py
python scripts/seed_ev_csv_fleet_data.py
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

The current React web app is still mostly frontend/mock-service based. Backend API integration is planned for the next phase.

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

### 4.2 Run Web App

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

### 4.3 Web App Checks

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

The current Flutter Android app is a frontend prototype with local mock services. Backend sync, GPS streaming, push notifications, and real maps are later phases.

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
flutter run
```

### Git Bash

```bash
flutter emulators --launch <emulator_id>
flutter devices
flutter run
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

For future backend-connected mobile testing over USB, reverse the backend port:

### PowerShell

```powershell
adb reverse tcp:8000 tcp:8000
```

### Git Bash

```bash
adb reverse tcp:8000 tcp:8000
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
- React web app is still not fully connected to backend APIs.
- Flutter app is still not fully connected to backend APIs.
- Phase 07 should connect the React web app services to the backend CRUD APIs.
- Phase 08 should connect the Flutter driver app services to the backend APIs.
