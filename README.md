# FleetOpt AI

FleetOpt AI is a research fleet-operations platform with:

- a FastAPI and MongoDB backend;
- a React and Vite web administration application;
- a Flutter Android driver application;
- predictive-maintenance, demand-forecasting, parcel-consolidation, load-balancing, route-dispatch, and live-trip workflows.

This guide uses **Git Bash on Windows**. Run each service in a separate Git Bash terminal and keep the terminals open while using the platform.

## 1. Prerequisites

Install the following tools before cloning the project:

- Git for Windows with Git Bash;
- Python 3.10 or 3.11;
- Node.js 22 or 24 with npm;
- Flutter 3.41 or a compatible stable release;
- Android Studio or the Android SDK Platform Tools;
- an Android phone with Developer Options and USB Debugging enabled;
- access to the approved MongoDB deployment configuration.

Verify the tools in Git Bash:

```bash
git --version
py -3.10 --version
node --version
npm --version
flutter --version
adb version
```

If Python 3.10 is unavailable but Python 3.11 is installed, replace `py -3.10` with `py -3.11` in the commands below.

## 2. Clone the Development Branch

Open Git Bash in the parent directory where the project should be stored:

```bash
cd "/e/PROJECTS/Out Source Project"
git clone --branch codex/development --single-branch https://github.com/MrAlfaa/Fleet-Optimization.git
cd Fleet-Optimization
```

Confirm the selected branch:

```bash
git branch --show-current
git status
```

The branch should be `codex/development` and the working tree should be clean.

To receive later changes:

```bash
git checkout codex/development
git pull --ff-only origin codex/development
```

## 3. Configure the Backend

The real `backend/.env` file contains private MongoDB and JWT values and is intentionally not stored in GitHub. The project owner must provide this file securely.

For a new local configuration, open Git Bash from the repository root:

```bash
cd backend
cp .env.example .env
notepad.exe .env
```

Set the real values for at least:

```dotenv
MONGODB_URI=mongodb+srv://<username>:<password>@<approved-host>/?appName=fleetoptimization
MONGODB_DB_NAME=fleet_optimization
JWT_SECRET_KEY=<long-random-secret>

MONGODB_TARGET_VALIDATION_ENABLED=true
ALLOWED_MONGODB_HOSTS=<approved-host-without-credentials>
ALLOWED_MONGODB_DATABASES=fleet_optimization
```

Important:

- Do not add `backend/.env` to Git.
- `ALLOWED_MONGODB_HOSTS` contains only the host name, not the full URL or credentials.
- The configured MongoDB host and database must match their allowlists.
- Environment changes take effect only after restarting the backend.

## 4. Terminal 1 - Run the Backend API

Open a new Git Bash terminal:

```bash
cd "/e/PROJECTS/Out Source Project/Fleet-Optimization/backend"
py -3.10 -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

For later runs, the environment already exists, so use:

```bash
cd "/e/PROJECTS/Out Source Project/Fleet-Optimization/backend"
source .venv/Scripts/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify the backend from another terminal:

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/health/db
```

The API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## 5. Terminal 2 - Run the Web Application

Keep Terminal 1 running. Open another Git Bash terminal:

```bash
cd "/e/PROJECTS/Out Source Project/Fleet-Optimization/Fleet_Web_App/frontend"
cp .env.example .env
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

For later runs:

```bash
cd "/e/PROJECTS/Out Source Project/Fleet-Optimization/Fleet_Web_App/frontend"
npm run dev -- --host 127.0.0.1 --port 5173
```

Open the web application:

```text
http://127.0.0.1:5173
```

The frontend uses `/api`, and the Vite development proxy forwards requests to `http://127.0.0.1:8000`.

## 6. Terminal 3 - Run the Load Optimization Worker

The worker is required when generating load-balancing candidates. Without it, a job can remain at `awaiting worker`.

Open another Git Bash terminal:

```bash
cd "/e/PROJECTS/Out Source Project/Fleet-Optimization/backend"
py -3.10 -m venv .venv-optimizer
source .venv-optimizer/Scripts/activate
python -m pip install --upgrade pip
python -m pip install -r optimizer-requirements.txt
python -m app.workers.load_optimization_worker
```

For later runs:

```bash
cd "/e/PROJECTS/Out Source Project/Fleet-Optimization/backend"
source .venv-optimizer/Scripts/activate
python -m app.workers.load_optimization_worker
```

The worker and backend must use the same `backend/.env` and MongoDB database.

## 7. Terminal 4 - Run the Android App on a Physical Phone

Keep the backend running on port `8000`.

### Prepare the phone

1. Enable Developer Options.
2. Enable USB Debugging.
3. Connect the phone with a data-capable USB cable.
4. Accept the USB debugging authorization dialog on the phone.

Open a new Git Bash terminal and verify the device:

```bash
adb devices
flutter devices
```

The device must be listed as `device`, not `unauthorized` or `offline`.

Forward the phone's port `8000` to the PC backend:

```bash
adb reverse tcp:8000 tcp:8000
adb reverse --list
```

Run the Flutter app. Set `DEVICE_ID` to the value shown by `flutter devices`:

```bash
cd "/e/PROJECTS/Out Source Project/Fleet-Optimization/Fleet_Mobile_App/frontend"
flutter pub get
DEVICE_ID="DEVICE_ID_FROM_FLUTTER_DEVICES"
flutter run -d "$DEVICE_ID" --dart-define=FLEETOPT_API_BASE_URL=http://127.0.0.1:8000/api
```

Run `adb reverse tcp:8000 tcp:8000` again whenever the phone is disconnected, restarted, or reconnected.

## 8. Recommended Startup Order

Start the system in this order:

1. Backend API on `127.0.0.1:8000`.
2. Load optimization worker.
3. Web application on `127.0.0.1:5173`.
4. Android driver application through USB and `adb reverse`.

## 9. Stop the Applications

In each running Git Bash terminal, press:

```text
Ctrl+C
```

Deactivate Python environments when finished:

```bash
deactivate
```

Remove the USB port forwarding when required:

```bash
adb reverse --remove tcp:8000
```

## 10. Troubleshooting

### Backend cannot connect to MongoDB

Check:

```bash
curl http://127.0.0.1:8000/api/health/db
```

Confirm that `MONGODB_URI`, `MONGODB_DB_NAME`, `ALLOWED_MONGODB_HOSTS`, and `ALLOWED_MONGODB_DATABASES` match. A different MongoDB host or database is rejected during backend startup when target validation is enabled.

### Web page cannot reach the backend

Confirm that the backend terminal is still running and that this endpoint responds:

```bash
curl http://127.0.0.1:8000/api/health
```

Then restart the Vite frontend.

### Android app cannot reach the backend

Run:

```bash
adb devices
adb reverse tcp:8000 tcp:8000
curl http://127.0.0.1:8000/api/health
```

Then stop and run the Flutter command again with:

```bash
--dart-define=FLEETOPT_API_BASE_URL=http://127.0.0.1:8000/api
```

### Load candidate remains at `awaiting worker`

Confirm that Terminal 3 is still running and connected to the same MongoDB database as the backend.

## 11. Security Notes

- Never commit `.env`, passwords, JWT secrets, MongoDB credentials, or private keys.
- Use only the supplied research database and authorized test accounts.
- Keep backend authorization enabled; frontend route controls are not a replacement for API authorization.
- Do not expose the local development ports directly to the public internet.
