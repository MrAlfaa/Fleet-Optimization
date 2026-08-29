# Isolated Load Optimization Worker

The API and optimization worker intentionally use different virtual environments. The API keeps the scikit-learn version required by the deployed ML artifacts.

```powershell
py -3.10 -m venv .venv-optimizer
.\.venv-optimizer\Scripts\python.exe -m pip install --upgrade pip
.\.venv-optimizer\Scripts\python.exe -m pip install -r optimizer-requirements.txt
.\.venv-optimizer\Scripts\python.exe -m app.workers.load_optimization_worker
```

Use `--once` for a health or deployment check. The worker leases MongoDB jobs, emits heartbeats, recovers stale leases, and releases parcel reservations when a job fails.
