"""Сквозная проверка живого API на Postgres: роли, права, сценарии отпуска, гонки, демо, CORS.

    docker compose up -d && cd backend && uv run python scripts/smoke_api.py [http://localhost:8000]

ВНИМАНИЕ: делает POST /api/demo/reset — стирает данные демо.
"""
import asyncio
import sys
from datetime import date, timedelta

import httpx
import jwt as pyjwt

B = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/") + "/api"
results: list[tuple[bool, str]] = []


def check(cond: bool, name: str, extra: object = "") -> None:
    results.append((bool(cond), name))
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f"  -> {extra}"))


async def main() -> None:
    async with httpx.AsyncClient(base_url=B, timeout=20) as c:
        await c.post("/demo/reset")
        tok = {}
        for login in ["aigerim", "nurlan", "asel", "erlan", "gulnara", "daniyar", "bakyt", "aibek"]:
            r = await c.post("/auth/login", json={"login": login, "password": "demo1234"})
            check(r.status_code == 200, f"login {login}", r.text)
            tok[login] = {"Authorization": f"Bearer {r.json()['accessToken']}"}
        H = tok
        today = date.fromisoformat((await c.get("/demo/state")).json()["now"][:10])

        # --- auth
        r = await c.post("/auth/login", json={"login": "aigerim", "password": "bad"})
        check(r.status_code == 401 and r.json()["code"] == "INVALID_CREDENTIALS", "wrong password 401")
        r = await c.get("/auth/me", headers={"Authorization": "Bearer garbage"})
        check(r.status_code == 401, "garbage token 401")
        forged = pyjwt.encode({"sub": "emp-daniyar", "role": "HRAdmin"}, "x" * 40, algorithm="HS256")
        r = await c.get("/requests", headers={"Authorization": f"Bearer {forged}"})
        check(r.status_code == 401, "forged token (other secret) 401")
        r = await c.post("/auth/login", json={"login": "aigerim"})
        check(r.status_code == 422 and r.json()["kind"] == "validation" and "password" in r.json()["fieldErrors"], "missing field -> 422 fieldErrors", r.text)

        # --- profile / access matrix
        for login in H:
            r = await c.get("/profile/me", headers=H[login])
            check(r.status_code == 200 and r.json()["monthlyBase"] is not None, f"profile/me {login}")
        matrix = [
            ("aigerim", "emp-nurlan", 403), ("erlan", "emp-aigerim", 200), ("erlan", "emp-asel", 403),
            ("aibek", "emp-aigerim", 403), ("aibek", "emp-bakyt", 200), ("daniyar", "emp-bakyt", 200),
            ("gulnara", "emp-erlan", 403), ("bakyt", "emp-aibek", 403),
        ]
        for who, target, code in matrix:
            r = await c.get(f"/employees/{target}", headers=H[who])
            check(r.status_code == code, f"{who} -> {target} = {code}", r.status_code)
        r = await c.get("/employees/emp-aigerim", headers=H["erlan"])
        check(r.json()["monthlyBase"] is None, "manager does not see team salary")
        r = await c.get("/employees/emp-aigerim", headers=H["daniyar"])
        check(r.json()["monthlyBase"] == 240000, "HR sees salary")
        team = await c.get("/team", headers=H["erlan"])
        check({e["id"] for e in team.json()["items"]} == {"emp-aigerim", "emp-nurlan"}, "erlan team")
        team = await c.get("/team", headers=H["aibek"])
        check({e["id"] for e in team.json()["items"]} == {"emp-bakyt"}, "aibek team (KG)")
        check((await c.get("/team", headers=H["aigerim"])).status_code == 403, "employee /team 403")
        r = await c.get("/employees?country=KG", headers=H["daniyar"])
        check({e["id"] for e in r.json()["items"]} == {"emp-bakyt", "emp-aibek"}, "HR employees by country")
        check((await c.get("/employees", headers=H["erlan"])).status_code == 403, "manager /employees 403")

        # --- leave: approve flow (KZ)
        pend = (await c.get("/leave/requests/pending", headers=H["erlan"])).json()["items"]
        check(len(pend) == 1 and pend[0]["employeeId"] == "emp-aigerim", "erlan pending = aigerim leave")
        rid = pend[0]["id"]
        check((await c.get(f"/leave/requests/{rid}", headers=H["nurlan"])).status_code == 403, "colleague cannot read leave by id")
        check((await c.get("/leave/requests/pending", headers=H["aigerim"])).status_code == 403, "employee pending 403")
        bal0 = (await c.get("/leave/balance", headers=H["aigerim"])).json()
        check(bal0["days"] == 24 and bal0["pendingDays"] == 7, "balance before", bal0)
        r = await c.post(f"/leave/requests/{rid}/decision", headers=H["erlan"], json={"decision": "Approved", "expectedVersion": 1})
        check(r.status_code == 200 and r.json()["status"] == "Approved", "erlan approves", r.text)
        check((await c.get("/leave/balance", headers=H["aigerim"])).json()["days"] == 17, "balance 24 -> 17 via 1C order")
        n = (await c.get("/notifications?unreadOnly=true", headers=H["aigerim"])).json()["items"]
        check(any(x["target"].get("requestId") == rid for x in n), "aigerim notified")
        my = (await c.get("/requests/my", headers=H["aigerim"])).json()["items"]
        check(my[0]["typeTitle"] == "Отпуск" and my[0]["permissions"]["canCancel"] is False, "my requests generic view")

        # --- leave: reject flow (KG)
        start = today + timedelta(days=30)
        r = await c.post("/leave/requests", headers=H["bakyt"], json={"submissionKey": "e2e-b1", "startDate": str(start), "endDate": str(start + timedelta(days=4)), "comment": "Той"})
        check(r.status_code == 201 and r.json()["managerId"] == "emp-aibek", "bakyt submits -> aibek", r.text)
        bid = r.json()["id"]
        check(any(x["target"].get("requestId") == bid for x in (await c.get("/notifications", headers=H["aibek"])).json()["items"]), "aibek notified of new request")
        check((await c.get(f"/requests/{bid}", headers=H["erlan"])).status_code == 403, "KZ manager cannot see KG request")
        r = await c.post(f"/leave/requests/{bid}/decision", headers=H["aibek"], json={"decision": "Rejected", "expectedVersion": 1})
        check(r.status_code == 422 and r.json()["code"] == "COMMENT_REQUIRED", "reject w/o comment 422")
        r = await c.post(f"/leave/requests/{bid}/decision", headers=H["aibek"], json={"decision": "Rejected", "expectedVersion": 1, "comment": "Инвентаризация склада"})
        check(r.status_code == 200 and r.json()["decisionComment"] == "Инвентаризация склада", "aibek rejects with reason")
        n = (await c.get("/notifications?unreadOnly=true", headers=H["bakyt"])).json()["items"]
        check(any("Инвентаризация склада" in x["message"] for x in n), "bakyt sees reason in notification", n)
        check((await c.get("/leave/balance", headers=H["bakyt"])).json()["days"] == 18, "rejected leave keeps balance")

        # --- cancel
        r = await c.post("/leave/requests", headers=H["asel"], json={"submissionKey": "e2e-a1", "startDate": str(start), "endDate": str(start + timedelta(days=1))})
        aid = r.json()["id"]
        check((await c.post(f"/requests/{aid}/cancel", headers=H["gulnara"])).status_code == 403, "manager cannot cancel employee request")
        r = await c.post(f"/requests/{aid}/cancel", headers=H["asel"])
        check(r.status_code == 200 and r.json()["status"] == "Cancelled", "asel cancels")
        check((await c.post(f"/requests/{aid}/cancel", headers=H["asel"])).status_code == 409, "cancel twice 409")
        check(all(x["id"] != aid for x in (await c.get("/leave/requests/pending", headers=H["gulnara"])).json()["items"]), "cancelled not in pending")
        r = await c.post("/leave/requests", headers=H["asel"], json={"submissionKey": "e2e-a2", "startDate": str(start), "endDate": str(start + timedelta(days=1))})
        check(r.status_code == 201, "after cancel same dates can be resubmitted", r.text)

        # --- race: two decisions at once
        r = await c.post("/leave/requests", headers=H["nurlan"], json={"submissionKey": "e2e-race", "startDate": str(start), "endDate": str(start + timedelta(days=2))})
        nid = r.json()["id"]
        a, b = await asyncio.gather(
            c.post(f"/leave/requests/{nid}/decision", headers=H["erlan"], json={"decision": "Approved", "expectedVersion": 1}),
            c.post(f"/leave/requests/{nid}/decision", headers=H["erlan"], json={"decision": "Rejected", "expectedVersion": 1, "comment": "гонка"}),
        )
        codes = sorted([a.status_code, b.status_code])
        final = (await c.get(f"/requests/{nid}", headers=H["erlan"])).json()
        decided_events = [e for e in final["history"] if e["event"] in ("approved", "rejected")]
        check(codes[0] == 200 and codes[1] in (403, 409) and len(decided_events) == 1, "race: exactly one decision wins", (codes, len(decided_events), final["status"]))

        # --- race: double submit same key
        s2 = today + timedelta(days=60)
        body = {"submissionKey": "e2e-dbl", "startDate": str(s2), "endDate": str(s2)}
        a, b = await asyncio.gather(*(c.post("/leave/requests", headers=H["aigerim"], json=body) for _ in range(2)))
        ids = {x.json().get("id") for x in (a, b) if x.status_code == 201}
        check({a.status_code, b.status_code} <= {201, 409} and len(ids) <= 1 and 201 in (a.status_code, b.status_code), "race: double submit -> one request", (a.status_code, b.status_code, a.text[:120], b.text[:120]))

        # --- race: numbering under concurrent creates
        s3 = today + timedelta(days=90)
        rs = await asyncio.gather(*(
            c.post("/leave/requests", headers=H[l], json={"submissionKey": "e2e-num", "startDate": str(s3), "endDate": str(s3)})
            for l in ("nurlan", "asel", "bakyt", "erlan")
        ))
        check(all(x.status_code == 201 for x in rs), "race: concurrent creates by different people", [(x.status_code, x.text[:100]) for x in rs])

        # --- HR
        reg = (await c.get("/requests", headers=H["daniyar"])).json()["items"]
        check(len(reg) >= 6, "HR registry", len(reg))
        kg = (await c.get("/requests?country=KG", headers=H["daniyar"])).json()["items"]
        check(kg and all(x["employeeId"] == "emp-bakyt" for x in kg), "HR registry filter KG")
        check((await c.get("/requests/types", headers=H["aigerim"])).json()[0]["code"] == "leave", "request types")

        # --- notifications
        other = (await c.get("/notifications", headers=H["erlan"])).json()["items"][0]["id"]
        check((await c.post(f"/notifications/{other}/read", headers=H["aigerim"])).status_code == 404, "cannot read other's notification")
        await c.post("/notifications/read-all", headers=H["aigerim"])
        check((await c.get("/notifications/unread-count", headers=H["aigerim"])).json()["unread"] == 0, "read-all")

        # --- kk
        await c.put("/auth/me/lang", headers=H["bakyt"], json={"lang": "kk"})
        n = (await c.get("/notifications", headers=H["bakyt"])).json()["items"][0]
        check(n["title"] == "Өтінім қабылданбады", "kk notification", n["title"])
        check((await c.put("/auth/me/lang", headers=H["bakyt"], json={"lang": "en"})).status_code == 422, "unknown lang 422")

        # --- demo time
        st = (await c.post("/demo/advance-time", json={"hours": 24 * 31})).json()
        check(st["offsetHours"] == 744, "advance 31 days")
        r = await c.post("/leave/requests", headers=H["nurlan"], json={"submissionKey": "e2e-t", "startDate": str(today + timedelta(days=5)), "endDate": str(today + timedelta(days=5))})
        check(r.status_code == 422 and r.json()["code"] == "START_IN_PAST", "shifted clock affects rules")
        r = await c.get("/auth/me", headers=H["aigerim"])
        check(r.status_code == 200, "token survives time travel")
        await c.post("/demo/reset")
        st = (await c.get("/demo/state")).json()
        pend = (await c.get("/leave/requests/pending", headers=H["erlan"])).json()["items"]
        check(st["offsetHours"] == 0 and len(pend) == 1, "reset restores seed + clock")
        check((await c.get("/notifications/unread-count", headers=H["erlan"])).json()["unread"] == 1, "seed: only fresh notification unread")

        # --- CORS
        r = await c.options("/leave/requests", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"})
        check(r.headers.get("access-control-allow-origin") == "http://localhost:5173", "CORS preflight from :5173")
        r = await c.options("/leave/requests", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"})
        check(r.headers.get("access-control-allow-origin") is None, "CORS rejects foreign origin")

    failed = [n for ok, n in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED:", failed)
        sys.exit(1)


asyncio.run(main())
