"""Скорость основных эндпоинтов на seed (QA А7): p50 / p95 / max по 20 запросам.

    docker compose up -d && cd backend && uv run python scripts/perf_check.py
"""

import asyncio
import statistics
import sys
import time

import httpx

B = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/") + "/api"
N = 20


async def main() -> None:
    async with httpx.AsyncClient(base_url=B, timeout=30) as c:
        async def tok(login: str) -> dict[str, str]:
            r = await c.post("/auth/login", json={"login": login, "password": "demo1234"})
            return {"Authorization": f"Bearer {r.json()['accessToken']}"}

        A, E, D = await tok("aigerim"), await tok("erlan"), await tok("daniyar")
        cases = [
            ("POST /auth/login", "POST", "/auth/login", None, {"login": "aigerim", "password": "demo1234"}),
            ("GET /profile/me", "GET", "/profile/me", A, None),
            ("GET /requests/my", "GET", "/requests/my", A, None),
            ("GET /leave/pending", "GET", "/leave/pending", E, None),
            ("GET /requests/all (HR)", "GET", "/requests/all", D, None),
            ("GET /notifications", "GET", "/notifications", A, None),
            ("GET /academy/my", "GET", "/academy/my", A, None),
            ("GET /ext/wage/summary", "GET", "/ext/wage/summary", A, None),
            ("GET /ext/ladder/me", "GET", "/ext/ladder/me", A, None),
            ("GET /ext/hr/risks (HR)", "GET", "/ext/hr/risks", D, None),
            ("GET /ext/hr/xray (HR)", "GET", "/ext/hr/xray", D, None),
            ("POST /ai/ask (без LLM)", "POST", "/ai/ask", A, {"question": "Сколько дней отпуска положено?"}),
            ("POST /ai/ask вне базы", "POST", "/ai/ask", A, {"question": "Есть ли медицинская страховка?"}),
        ]
        print(f"{'Эндпоинт':32} {'p50 мс':>8} {'p95 мс':>8} {'max мс':>8}")
        worst = 0.0
        for name, method, path, headers, body in cases:
            times = []
            for _ in range(N):
                t0 = time.perf_counter()
                r = await c.request(method, path, headers=headers, json=body)
                times.append((time.perf_counter() - t0) * 1000)
                assert r.status_code < 400, (name, r.status_code)
            times.sort()
            p95 = times[int(N * 0.95) - 1]
            worst = max(worst, p95)
            print(f"{name:32} {statistics.median(times):8.0f} {p95:8.0f} {times[-1]:8.0f}")
        print(f"\nХудший p95: {worst:.0f} мс — {'OK (< 500 мс)' if worst < 500 else 'МЕДЛЕННО'}")


asyncio.run(main())
