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
        r = await c.get("/requests/all", headers={"Authorization": f"Bearer {forged}"})
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
        pend = (await c.get("/leave/pending", headers=H["erlan"])).json()["items"]
        check(len(pend) == 1 and pend[0]["employeeId"] == "emp-aigerim", "erlan pending = aigerim leave", pend)
        rid = pend[0]["id"]
        check((await c.get(f"/leave/{rid}", headers=H["nurlan"])).status_code == 403, "colleague cannot read leave by id")
        check((await c.get("/leave/pending", headers=H["aigerim"])).status_code == 403, "employee pending 403")
        bal0 = (await c.get("/leave/balance", headers=H["aigerim"])).json()
        check(bal0["days"] == 21 and bal0["pendingDays"] == 7 and bal0["availableDays"] == 14, "balance before", bal0)
        r = await c.post(f"/leave/{rid}/decision", headers=H["erlan"], json={"decision": "Approved", "expectedVersion": 1})
        check(r.status_code == 200 and r.json()["status"] == "Approved", "erlan approves", r.text)
        check((await c.get("/leave/balance", headers=H["aigerim"])).json()["days"] == 14, "balance 21 -> 14 after approval")
        n = (await c.get("/notifications?unreadOnly=true", headers=H["aigerim"])).json()["items"]
        check(any(x["target"].get("requestId") == rid for x in n), "aigerim notified")
        my = (await c.get("/requests/my", headers=H["aigerim"])).json()["items"]
        check(my[0]["typeTitle"] == "Отпуск" and my[0]["permissions"]["canCancel"] is False, "my requests generic view")

        # --- leave: reject flow (KG)
        start = today + timedelta(days=30)
        r = await c.post("/leave", headers=H["bakyt"], json={"submissionKey": "e2e-b1", "startDate": str(start), "endDate": str(start + timedelta(days=4)), "comment": "Той"})
        check(r.status_code == 201 and r.json()["managerId"] == "emp-aibek", "bakyt submits -> aibek", r.text)
        bid = r.json()["id"]
        check(any(x["target"].get("requestId") == bid for x in (await c.get("/notifications", headers=H["aibek"])).json()["items"]), "aibek notified of new request")
        check((await c.get(f"/requests/{bid}", headers=H["erlan"])).status_code == 403, "KZ manager cannot see KG request")
        r = await c.post(f"/leave/{bid}/decision", headers=H["aibek"], json={"decision": "Rejected", "expectedVersion": 1})
        check(r.status_code == 422 and r.json()["code"] == "COMMENT_REQUIRED", "reject w/o comment 422")
        r = await c.post(f"/leave/{bid}/decision", headers=H["aibek"], json={"decision": "Rejected", "expectedVersion": 1, "comment": "Инвентаризация склада", "reasonCode": "STAFFING"})
        check(r.status_code == 200 and r.json()["decisionComment"] == "Инвентаризация склада", "aibek rejects with reason")
        n = (await c.get("/notifications?unreadOnly=true", headers=H["bakyt"])).json()["items"]
        check(any("Инвентаризация склада" in x["message"] for x in n), "bakyt sees reason in notification", n)
        check((await c.get("/leave/balance", headers=H["bakyt"])).json()["days"] == 18, "rejected leave keeps balance")

        # --- cancel
        r = await c.post("/leave", headers=H["asel"], json={"submissionKey": "e2e-a1", "startDate": str(start), "endDate": str(start + timedelta(days=1))})
        aid = r.json()["id"]
        check((await c.post(f"/requests/{aid}/cancel", headers=H["gulnara"])).status_code == 403, "manager cannot cancel employee request")
        r = await c.post(f"/requests/{aid}/cancel", headers=H["asel"])
        check(r.status_code == 200 and r.json()["status"] == "Cancelled", "asel cancels")
        check((await c.post(f"/requests/{aid}/cancel", headers=H["asel"])).status_code == 409, "cancel twice 409")
        check(all(x["id"] != aid for x in (await c.get("/leave/pending", headers=H["gulnara"])).json()["items"]), "cancelled not in pending")
        r = await c.post("/leave", headers=H["asel"], json={"submissionKey": "e2e-a2", "startDate": str(start), "endDate": str(start + timedelta(days=1))})
        check(r.status_code == 201, "after cancel same dates can be resubmitted", r.text)

        # --- race: two decisions at once
        r = await c.post("/leave", headers=H["nurlan"], json={"submissionKey": "e2e-race", "startDate": str(start), "endDate": str(start + timedelta(days=2))})
        nid = r.json()["id"]
        a, b = await asyncio.gather(
            c.post(f"/leave/{nid}/decision", headers=H["erlan"], json={"decision": "Approved", "expectedVersion": 1}),
            c.post(f"/leave/{nid}/decision", headers=H["erlan"], json={"decision": "Rejected", "expectedVersion": 1, "comment": "гонка решений", "reasonCode": "OTHER"}),
        )
        codes = sorted([a.status_code, b.status_code])
        final = (await c.get(f"/requests/{nid}", headers=H["erlan"])).json()
        decided_events = [e for e in final["history"] if e["event"] in ("approved", "rejected")]
        check(codes[0] == 200 and codes[1] in (403, 409) and len(decided_events) == 1, "race: exactly one decision wins", (codes, len(decided_events), final["status"]))

        # --- race: double submit same key
        s2 = today + timedelta(days=60)
        body = {"submissionKey": "e2e-dbl", "startDate": str(s2), "endDate": str(s2)}
        a, b = await asyncio.gather(*(c.post("/leave", headers=H["aigerim"], json=body) for _ in range(2)))
        ids = {x.json().get("id") for x in (a, b) if x.status_code == 201}
        check({a.status_code, b.status_code} <= {201, 409} and len(ids) <= 1 and 201 in (a.status_code, b.status_code), "race: double submit -> one request", (a.status_code, b.status_code, a.text[:120], b.text[:120]))

        # --- race: numbering under concurrent creates
        s3 = today + timedelta(days=90)
        rs = await asyncio.gather(*(
            c.post("/leave", headers=H[l], json={"submissionKey": "e2e-num", "startDate": str(s3), "endDate": str(s3)})
            for l in ("nurlan", "asel", "bakyt", "erlan")
        ))
        check(all(x.status_code == 201 for x in rs), "race: concurrent creates by different people", [(x.status_code, x.text[:100]) for x in rs])

        # --- HR
        reg = (await c.get("/requests/all", headers=H["daniyar"])).json()["items"]
        check(len(reg) >= 8, "HR registry", len(reg))
        kg = (await c.get("/requests/all?country=KG", headers=H["daniyar"])).json()["items"]
        check(len(kg) >= 2 and all(x["employeeId"] == "emp-bakyt" for x in kg), "HR registry filter KG")
        check((await c.get("/requests/types", headers=H["aigerim"])).json()[0]["code"] == "vacation", "request types")

        # --- card documents, role login, hr question
        card = (await c.get(f"/leave/{rid}", headers=H["aigerim"])).json()
        check(card["documents"] and card["documents"][0]["kind"] == "leave_order", "card shows leave order document")
        r = await c.post("/demo/login-as", json={"role": "Manager"})
        check(r.json()["user"]["id"] == "emp-erlan", "demo login by role")
        r = await c.post("/hr-questions", headers=H["asel"], json={"question": "Сколько дней отпуска за вредность?"})
        check(r.status_code == 201, "hr question created", r.text)
        hq = r.json()["id"]
        check((await c.get(f"/requests/{hq}", headers=H["gulnara"])).status_code == 403, "manager cannot see hr question")
        r = await c.post(f"/requests/{hq}/decide", headers=H["daniyar"], json={"decision": "Approved", "comment": "Для сортировщиков не предусмотрено."})
        check(r.status_code == 200, "HR answers question")
        n = (await c.get("/notifications?unreadOnly=true", headers=H["asel"])).json()["items"]
        check(any("не предусмотрено" in x["message"] for x in n), "author gets HR answer")
        r = await c.get("/requests/all?unitId=kz-almaty-sc-a", headers=H["daniyar"])
        check(all(x["employeeId"] == "emp-asel" for x in r.json()["items"]), "HR registry filter unit")

        # --- academy
        my = (await c.get("/academy/my", headers=H["aigerim"])).json()["items"]
        check({x["id"] for x in my} == {"course-returns", "course-safety"}, "academy: aigerim has 2 courses")
        det = (await c.get("/academy/courses/course-safety", headers=H["aigerim"])).json()
        check(all(set(q) == {"id", "ord", "text", "options"} for q in det["questions"]), "academy: no correct answers leaked")
        for lid in ("l-saf-2", "l-saf-3", "l-saf-4"):
            await c.post(f"/academy/lessons/{lid}/complete", headers=H["aigerim"])
        r = await c.post("/academy/courses/course-safety/submit", headers=H["aigerim"], json={"answers": [1, 1, 1, 0]})
        check(r.json().get("passed") is True, "academy: pass test", r.text)
        prof = (await c.get("/profile/me", headers=H["aigerim"])).json()
        check(all(t["status"] == "Completed" for t in prof["assignedTraining"]), "academy: profile shows completed")
        r = await c.post("/academy/assignments", headers=H["erlan"], json={"employeeId": "emp-asel", "courseId": "course-safety"})
        check(r.status_code == 403, "academy: manager cannot assign other team")
        r = await c.post("/academy/assignments", headers=H["gulnara"], json={"employeeId": "emp-asel", "courseId": "course-safety"})
        check(r.status_code == 201, "academy: manager assigns own team")
        check(any(n["kind"] == "academy.assigned" for n in (await c.get("/notifications", headers=H["asel"])).json()["items"]), "academy: assigned notification")

        # --- guarantees
        card = (await c.get(f"/leave/{pend[0]['id']}", headers=H["aigerim"])).json()
        check("guarantee" in card["extensions"], "guarantee badge in card")
        r = await c.post("/leave", headers=H["asel"], json={"submissionKey": "e2e-g", "startDate": str(today + timedelta(days=100)), "endDate": str(today + timedelta(days=100))})
        gid = r.json()["id"]
        r = await c.post(f"/requests/{gid}/decide", headers=H["gulnara"], json={"decision": "Rejected", "comment": "Нет людей в смене А"})
        check(r.json().get("code") == "REASON_REQUIRED", "reject without reason -> REASON_REQUIRED", r.text)

        # --- wage access
        ws = (await c.get("/ext/wage/summary", headers=H["aigerim"])).json()
        check(ws["limitPct"] == 50 and ws["available"] == ws["earned"] // 2, "wage: summary 50%", ws)
        r = await c.post("/ext/wage/withdraw", headers=H["aigerim"], json={"amount": min(60000, ws["available"])})
        check(r.status_code == 201 and r.json()["summary"]["available"] == ws["available"] - min(60000, ws["available"]), "wage: withdraw", r.text)
        wr = (await c.get(f"/requests/{r.json()['requestId']}", headers=H["aigerim"])).json()
        check(wr["status"] == "Approved" and wr["decidedBySystem"], "wage: approved by system")
        r = await c.post("/ext/wage/withdraw", headers=H["aigerim"], json={"amount": 10_000_000})
        check(r.json().get("code") == "AMOUNT_EXCEEDS_AVAILABLE", "wage: over limit rejected")
        two = await asyncio.gather(*(c.post("/ext/wage/withdraw", headers=H["nurlan"], json={"amount": 5000}) for _ in range(3)))
        check(sorted(x.status_code for x in two) == [201, 201, 422], "wage: concurrent withdrawals respect limit", [x.status_code for x in two])

        # --- ladder
        lad = (await c.get("/ext/ladder/me", headers=H["aigerim"])).json()
        check(lad["current"]["code"] == "SORT-1" and lad["next"]["code"] == "SORT-2" and lad["raiseToNextMin"] == 35000, "ladder: aigerim SORT-1 -> SORT-2 +35 000", lad)
        check((await c.get("/ext/ladder/grades", headers=H["aigerim"])).status_code == 403, "ladder: employee cannot list all grades")

        # --- hr console
        cards = {x["employeeId"]: x for x in (await c.get("/ext/hr/risks?country=KZ", headers=H["daniyar"])).json()["items"]}
        check({"emp-aigerim", "emp-nurlan", "emp-asel"} <= set(cards), "radar: 3+ people at risk", list(cards))
        check((await c.get("/ext/hr/risks", headers=H["erlan"])).status_code == 403, "radar: manager 403")
        sv = (await c.get("/ext/hr/savings", headers=H["daniyar"])).json()
        sig = next(x for x in cards["emp-aigerim"]["signals"] if x["kind"] == "no_review")
        r = await c.post(f"/ext/hr/risks/{sig['id']}/propose-review", headers=H["daniyar"])
        check(r.status_code == 200 and r.json()["nextReviewDate"], "radar: propose review")
        await c.post(f"/ext/hr/risks/{sig['id']}/confirm-retained", headers=H["daniyar"])
        sv2 = (await c.get("/ext/hr/savings", headers=H["daniyar"])).json()
        check(sv2["saved"] - sv["saved"] == 900000, "radar: savings +900 000", (sv["saved"], sv2["saved"]))

        # --- ai jana
        a = (await c.post("/ai/ask", headers=H["aigerim"], json={"question": "Сколько дней отпуска положено?"})).json()
        check(a["answered"] and a["sources"][0]["articleId"] == "kb-kz-vacation", "ai: KZ answer with KZ source", a)
        a = (await c.post("/ai/ask", headers=H["bakyt"], json={"question": "Сколько дней отпуска положено?"})).json()
        check(a["answered"] and a["sources"][0]["articleId"] == "kb-kg-vacation", "ai: KG answer with KG source", a)
        a = (await c.post("/ai/ask", headers=H["aigerim"], json={"question": "Какая зарплата у моего начальника?"})).json()
        check(a["reason"] == "other_person" and not a["sources"], "ai: refuses other person's salary")
        a = (await c.post("/ai/ask", headers=H["aigerim"], json={"question": "Как оплачиваются ночные смены?"})).json()
        check(not a["answered"] and a["escalateAvailable"], "ai: honest no-answer + escalate")
        check((await c.get("/ai/sources/kb-kz-vacation", headers=H["bakyt"])).status_code == 404, "ai: other country source 404")

        # --- kb gaps
        gl = (await c.get("/ext/kb/gaps?country=KZ", headers=H["daniyar"])).json()
        check(gl and gl[0]["count"] >= 23 and "ночн" in gl[0]["label"].lower(), "kb gaps: night shifts group", [g["count"] for g in gl])
        d = (await c.post(f"/ext/kb/gaps/{gl[0]['id']}/draft", headers=H["daniyar"])).json()
        await c.put(f"/ext/kb/docs/{d['id']}", headers=H["daniyar"], json={"bodyMd": "## Оплата ночных смен\nНочные смены оплачиваются с доплатой 50% к ставке за смену."})
        await c.post(f"/ext/kb/docs/{d['id']}/publish", headers=H["daniyar"])
        a = (await c.post("/ai/ask", headers=H["aigerim"], json={"question": "Как оплачиваются ночные смены?"})).json()
        check(a["answered"] and a["sources"][0]["sourceLabel"].startswith("Внутреннее правило"), "kb gaps: published rule answers", a)

        # --- shifts
        mine = (await c.get("/ext/shifts/my", headers=H["aigerim"])).json()["items"]
        await c.post(f"/ext/shifts/{mine[0]['id']}/offer", headers=H["aigerim"])
        rs = await asyncio.gather(*(c.post(f"/ext/shifts/{mine[0]['id']}/take", headers=H[x]) for x in ("asel", "nurlan")))
        check(sorted(x.status_code for x in rs) == [200, 409], "shifts: two takers race -> one wins", [x.status_code for x in rs])
        op = next(x for x in (await c.get("/ext/shifts/available", headers=H["asel"])).json()["items"] if x["status"] == "open")
        check(op["payPreview"] == 12000, "shifts: open shift +12 000")

        # --- notifications
        other = (await c.get("/notifications", headers=H["erlan"])).json()["items"][0]["id"]
        check((await c.post(f"/notifications/{other}/read", headers=H["aigerim"])).status_code == 404, "cannot read other's notification")
        await c.post("/notifications/read-all", headers=H["aigerim"])
        check((await c.get("/notifications/unread-count", headers=H["aigerim"])).json()["unread"] == 0, "read-all")

        # --- kk
        await c.put("/auth/me/lang", headers=H["bakyt"], json={"lang": "kk"})
        n = next(x for x in (await c.get("/notifications", headers=H["bakyt"])).json()["items"] if x["kind"] == "request.decided")
        check(n["title"] == "Өтінім қабылданбады", "kk notification", n["title"])
        check((await c.put("/auth/me/lang", headers=H["bakyt"], json={"lang": "en"})).status_code == 422, "unknown lang 422")

        # --- demo time
        st = (await c.post("/demo/advance-time", json={"hours": 24 * 31})).json()
        check(st["offsetHours"] == 744, "advance 31 days")
        r = await c.post("/leave", headers=H["nurlan"], json={"submissionKey": "e2e-t", "startDate": str(today + timedelta(days=5)), "endDate": str(today + timedelta(days=5))})
        check(r.status_code == 422 and r.json()["code"] == "INVALID_DATES", "shifted clock affects rules", r.text)
        r = await c.get("/auth/me", headers=H["aigerim"])
        check(r.status_code == 200, "token survives time travel")
        await c.post("/demo/reset")
        st = (await c.get("/demo/state")).json()
        pend = (await c.get("/leave/pending", headers=H["erlan"])).json()["items"]
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
