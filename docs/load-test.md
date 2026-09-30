# PNG9 API load test

The dependency-light asyncio + httpx runner lives at `backend/loadtest/run.py`. It creates separate disposable student accounts for each virtual user directly in the configured local database, then exercises login, question retrieval, path reads, answer submission, and analytics reads. It does not require Locust, pywin32, or browser dependencies.

Example (run from `backend/`, after starting the backend against a disposable DB):

```powershell
$env:DATABASE_URL = 'sqlite:///./load-test.db'
$env:REDIS_URL = ''
$env:PYTHONPATH = '.venv-packages'
python -m loadtest.run --host http://127.0.0.1:8000 --users 50 --ramp 10 --duration 60 --provision
```

The harness uses 50 distinct accounts, so the backend's per-user 60-answer/minute limiter remains enabled and legitimate users are not combined behind one shared quota. Each user is paced to at most one answer per 1.1 seconds. The local load test returned no HTTP 429 responses. It is still a single-process SQLite stress run; SQLite's serialized write path limits answer throughput and should not be interpreted as PostgreSQL/Redis capacity.

## Latest run — 2026-10-01

- Host: Windows 11, Python 3.14.2, 8 logical processors (Intel64 family/model reported by the OS); the system API denied access to exact CPU model and RAM size.
- Backend: local FastAPI, one Uvicorn process, disposable SQLite `async-load-test.db`; Redis disabled (`REDIS_URL` empty).
- Load profile: 50 virtual users, 10-second ramp, then 60 seconds at target; 97.16 seconds wall time including request drain.
- Requests: 261 total; 179 HTTP 200, 8 HTTP 500, 74 client/network timeouts; **82 errors / 31.42% error rate**. There were **zero HTTP 429** responses.
- Measured request latency: p50 **777.17 ms**, p95 **31,982.10 ms**, p99 **41,523.34 ms**.
- Throughput: **2.69 requests/second** over full wall time.
- Workload counts: 50 logins, 22 question reads, 63 path reads, 63 answer posts, 63 analytics reads. Some question reads timed out while SQLite was contended, so not every virtual user completed the full workflow.

This run demonstrates the SQLite bottleneck rather than acceptable service-level performance: concurrent requests caused long waits, timeouts, and database errors. Do not use these results as a production capacity claim. Repeat against PostgreSQL (and Redis enabled) before setting capacity targets. The earlier harness setup attempt used the wrong disposable database and returned only login failures; it was discarded and is not included in the figures above.
