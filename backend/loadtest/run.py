"""Dependency-light asyncio load check: python -m loadtest.run --users 50 --duration 60."""

from __future__ import annotations

import argparse
import asyncio
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx


@dataclass
class Sample:
    operation: str
    duration_ms: float
    ok: bool
    status: int


async def main_run(base_url: str, users: int, duration: int, ramp_seconds: int, password: str) -> dict:
    samples: list[Sample] = []
    started = time.perf_counter()
    # Ramp-up time precedes the full requested steady-state duration.
    stop_at = started + ramp_seconds + duration
    gate = asyncio.Semaphore(users)

    async def worker(index: int) -> None:
        await asyncio.sleep(ramp_seconds * index / max(1, users - 1))
        email = f"load-{index}@png9.local"
        async with gate, httpx.AsyncClient(base_url=base_url, timeout=15.0) as client:

            async def request(method: str, path: str, *, json=None) -> httpx.Response | None:
                request_start = time.perf_counter()
                try:
                    response = await client.request(method, path, json=json)
                    samples.append(
                        Sample(
                            path,
                            (time.perf_counter() - request_start) * 1000,
                            response.is_success,
                            response.status_code,
                        )
                    )
                    return response
                except Exception:
                    samples.append(Sample(path, (time.perf_counter() - request_start) * 1000, False, 0))
                    return None

            login = await request("POST", "/api/auth/login", json={"email": email, "password": password})
            if not login or not login.is_success:
                return
            question_resp = await request("GET", "/api/questions/next")
            if not question_resp or not question_resp.is_success:
                return
            question = question_resp.json()
            session_id = question["sessionId"]
            sequence = 0
            while time.perf_counter() < stop_at:
                await request("GET", "/api/path")
                # Stay under the production per-user limit (60 answers/minute)
                # with a small margin; independent VUs use independent accounts.
                await request(
                    "POST",
                    "/api/interactions",
                    json={
                        "questionId": question["id"],
                        "answer": str(sequence % len(question["options"])),
                        "confidence": 3,
                        "timeTakenMs": 3500,
                        "sessionId": session_id,
                    },
                )
                await request("GET", "/api/analytics?period=7d")
                sequence += 1
                await asyncio.sleep(1.1)

    await asyncio.gather(*(worker(index) for index in range(users)))
    elapsed = time.perf_counter() - started
    latencies = [item.duration_ms for item in samples]
    sorted_values = sorted(latencies)

    def percentile(q: float) -> float | None:
        return (
            round(
                sorted_values[min(len(sorted_values) - 1, int((len(sorted_values) - 1) * q))],
                2,
            )
            if sorted_values
            else None
        )

    failures = sum(not item.ok for item in samples)
    return {
        "date": datetime.now(UTC).isoformat(),
        "baseUrl": base_url,
        "users": users,
        "durationSeconds": duration,
        "rampSeconds": ramp_seconds,
        "elapsedSeconds": round(elapsed, 2),
        "requests": len(samples),
        "errors": failures,
        "errorRate": failures / max(1, len(samples)),
        "throughputRps": round(len(samples) / max(elapsed, 0.001), 2),
        "latencyMs": {
            "p50": percentile(0.50),
            "p95": percentile(0.95),
            "p99": percentile(0.99),
        },
        "statusCounts": {
            str(status): sum(item.status == status for item in samples)
            for status in sorted({item.status for item in samples})
        },
        "operationCounts": {
            name: sum(item.operation == name for item in samples)
            for name in sorted({item.operation for item in samples})
        },
    }


def provision(users: int, password: str) -> None:
    """Create isolated disposable users directly in the configured local DB."""
    import bcrypt
    from sqlalchemy import select

    from app.models import SessionLocal, User

    db = SessionLocal()
    try:
        for index in range(users):
            email = f"load-{index}@png9.local"
            if db.scalar(select(User.id).where(User.email == email)):
                continue
            db.add(
                User(
                    email=email,
                    role="student",
                    hashed_password=bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode(),
                )
            )
        db.commit()
    finally:
        db.close()


async def async_main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="http://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=50)
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--ramp", type=int, default=10)
    parser.add_argument("--password", default=os.getenv("LOAD_TEST_PASSWORD", "LoadTestPass123!"))
    parser.add_argument(
        "--provision",
        action="store_true",
        help="seed disposable per-VU test accounts through local DB",
    )
    args = parser.parse_args()
    if args.users < 1 or args.users > 50 or args.duration < 1 or args.ramp < 0:
        parser.error("users must be 1..50, duration positive, and ramp nonnegative")
    if args.provision:
        provision(args.users, args.password)
    result = await main_run(args.host.rstrip("/"), args.users, args.duration, args.ramp, args.password)
    print(result)


if __name__ == "__main__":
    asyncio.run(async_main())
