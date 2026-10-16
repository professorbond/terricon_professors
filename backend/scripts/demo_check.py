"""Прогон демо-сценария CLAUDE.md §12 через API собранного приложения (по шагам, с чистой базы).

    docker compose up -d && cd backend && uv run python scripts/demo_check.py [http://localhost:8000]

ВНИМАНИЕ: делает POST /api/demo/reset.
"""

import asyncio
import sys

import httpx

B = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/") + "/api"
ok_all = True


def step(title: str, cond: bool, detail: object = "") -> None:
    global ok_all
    ok_all &= bool(cond)
    print(("  ✅ " if cond else "  ❌ ") + title + ("" if cond else f"  → {detail}"))


def money(v: int) -> str:
    return f"{v:,}".replace(",", " ") + " ₸"


async def main() -> None:
    async with httpx.AsyncClient(base_url=B, timeout=30) as c:
        await c.post("/demo/reset")

        async def as_(login: str) -> dict[str, str]:
            r = await c.post("/auth/login", json={"login": login, "password": "demo1234"})
            return {"Authorization": f"Bearer {r.json()['accessToken']}"}

        A, E, D, BK = await as_("aigerim"), await as_("erlan"), await as_("daniyar"), await as_("bakyt")

        print("1. Айгерим входит → главная и профиль")
        g = (await c.get("/ext/guarantees/summary/me", headers=A)).json()
        w = (await c.get("/ext/wage/summary", headers=A)).json()
        lad = (await c.get("/ext/ladder/me", headers=A)).json()
        step(f"«Мои гарантии»: ответ по отпуску до {g['openRequests'][0]['deadlineAt'][:16]}", len(g["openRequests"]) == 1)
        step(f"«Доступно {money(w['available'])}» · отработано {w['shiftsWorked']} смен · заработано {money(w['earned'])}", w["available"] == w["earned"] // 2)
        step(f"Лестница: осталось {lad['remainingCourses']} курс, +{money(lad['raiseToNextMin'])} к нижней границе", lad["remainingCourses"] == 1 and lad["raiseToNextMin"] == 35000)

        print("2. «Зарплата по факту»: 60 000 ₸")
        amount = min(60000, w["available"])
        r = await c.post("/ext/wage/withdraw", headers=A, json={"amount": amount})
        req = (await c.get(f"/requests/{r.json()['requestId']}", headers=A)).json()
        step(f"Выплата {money(amount)}: заявка {req['number']} «одобрено системой», документ {r.json()['documentNumber']}", req["decidedBySystem"] and req["status"] == "Approved")
        step("Уведомление «Деньги отправлены»", any(n["kind"] == "wage.paid" for n in (await c.get("/notifications", headers=A)).json()["items"]))

        print("3. Ерлан: отказ без причины нельзя, чужая смена — 403")
        pend = (await c.get("/leave/pending", headers=E)).json()["items"][0]
        r = await c.post(f"/leave/{pend['id']}/decision", headers=E, json={"decision": "Rejected", "expectedVersion": pend["version"], "comment": "Не могу отпустить"})
        step(f"Отказ без причины → {r.json().get('code')}", r.status_code == 422 and r.json()["code"] == "REASON_REQUIRED")
        step("Профиль сотрудника смены А → 403", (await c.get("/employees/emp-asel", headers=E)).status_code == 403)

        print("4. Демо «+2 дня» → отпуск «Одобрено по сроку»")
        await c.post("/demo/advance-time", json={"hours": 48})
        card = (await c.get(f"/leave/{pend['id']}", headers=A)).json()
        step(f"Статус {card['status']}, решение системы, resolution={card['extensions']['guarantee']['resolution']}", card["status"] == "Approved" and card["decidedBySystem"])
        await c.post("/demo/reset")  # дальше — с исходного состояния
        A, E, D, BK = await as_("aigerim"), await as_("erlan"), await as_("daniyar"), await as_("bakyt")

        print("5. Айгерим проходит курс → лестница «все курсы пройдены»")
        for lid in ("l-saf-2", "l-saf-3", "l-saf-4"):
            await c.post(f"/academy/lessons/{lid}/complete", headers=A)
        r = (await c.post("/academy/courses/course-safety/submit", headers=A, json={"answers": [1, 1, 1, 0]})).json()
        lad = (await c.get("/ext/ladder/me", headers=A)).json()
        step(f"Тест сдан на {r['score']}%, курсов осталось {lad['remainingCourses']}, готова к SORT-2: {lad['ready']}", r["passed"] and lad["remainingCourses"] == 0)

        print("6. AI Jana")
        kz = (await c.post("/ai/ask", headers=A, json={"question": "Сколько дней отпуска положено?"})).json()
        kg = (await c.post("/ai/ask", headers=BK, json={"question": "Сколько дней отпуска положено?"})).json()
        boss = (await c.post("/ai/ask", headers=A, json={"question": "Какая зарплата у моего начальника?"})).json()
        night = (await c.post("/ai/ask", headers=A, json={"question": "Как оплачиваются ночные смены?"})).json()
        step(f"Отпуск (KZ) → {kz['sources'][0]['sourceLabel']}", kz["answered"] and kz["sources"][0]["articleId"] == "kb-kz-vacation")
        step(f"Тот же вопрос от Бакыта (KG) → {kg['sources'][0]['sourceLabel']}", kg["answered"] and kg["sources"][0]["articleId"] == "kb-kg-vacation")
        step("«Зарплата начальника» → отказ без поиска", boss["reason"] == "other_person")
        step("«Ночные смены» → «нет информации» + «Спросить HR»", not night["answered"] and night["escalateAvailable"])
        r = await c.post("/hr-questions", headers=A, json={"question": "Как оплачиваются ночные смены?", "aiContext": night["message"]})
        step("«Спросить HR» → вопрос ушёл в HR", r.status_code == 201)

        print("7. Данияр (HR): радар и счётчик")
        cards = {x["employeeId"]: x for x in (await c.get("/ext/hr/risks?country=KZ", headers=D)).json()["items"]}
        kinds = {k: {s["kind"] for s in v["signals"]} for k, v in cards.items()}
        step(f"Радар: Айгерим {sorted(kinds.get('emp-aigerim', []))}, Нурлан {sorted(kinds.get('emp-nurlan', []))}", "pay_equity" in kinds.get("emp-aigerim", set()) and "rejections" in kinds.get("emp-nurlan", set()))
        step("Вопрос к HR, просроченный по сроку, виден в радаре", "open_grievance" in kinds.get("emp-nurlan", set()))
        sig = next(s for s in cards["emp-aigerim"]["signals"] if s["kind"] == "no_review")
        before = (await c.get("/ext/hr/savings", headers=D)).json()["saved"]
        r = (await c.post(f"/ext/hr/risks/{sig['id']}/propose-review", headers=D)).json()
        new_date = (await c.get("/ext/ladder/me", headers=A)).json()["nextReviewDate"]
        step(f"«Предложить пересмотр» → уведомление и новая дата в лестнице {new_date}", r["nextReviewDate"] == new_date)
        await c.post(f"/ext/hr/risks/{sig['id']}/confirm-retained", headers=D)
        after = (await c.get("/ext/hr/savings", headers=D)).json()["saved"]
        step(f"«Сотрудник остался» → {money(before)} → {money(after)}", (before, after) == (9_900_000, 10_800_000))

        print("8. Рентген и пробелы базы")
        xr = (await c.get("/ext/hr/xray", headers=D)).json()["items"]
        step(f"Рентген: наверху {xr[0]['managerName']} ({xr[0]['lateDecisions']} решения позже срока)", xr[0]["managerId"] == "emp-erlan")
        gap = (await c.get("/ext/kb/gaps?country=KZ", headers=D)).json()[0]
        doc = (await c.post(f"/ext/kb/gaps/{gap['id']}/draft", headers=D)).json()
        await c.put(f"/ext/kb/docs/{doc['id']}", headers=D, json={"bodyMd": "## Оплата ночных смен\nНочные смены оплачиваются с доплатой 50% к ставке за смену."})
        await c.post(f"/ext/kb/docs/{doc['id']}/publish", headers=D)
        night = (await c.post("/ai/ask", headers=A, json={"question": "Как оплачиваются ночные смены?"})).json()
        step(f"«{gap['count']} вопросов про ночные смены» → черновик → публикация → AI отвечает ({night['sources'][0]['sourceLabel'] if night['answered'] else '—'})", night["answered"])

        print("9. Биржа смен: Айгерим отдаёт, Асель берёт")
        S = await as_("asel")
        mine = (await c.get("/ext/shifts/my", headers=A)).json()["items"][0]
        await c.post(f"/ext/shifts/{mine['id']}/offer", headers=A)
        r = (await c.post(f"/ext/shifts/{mine['id']}/take", headers=S)).json()
        step(f"Смена {r['date']} {r['startTime']}–{r['endTime']} теперь у {r['assigneeName']}, +{money(r['payPreview'])}", r["assigneeId"] == "emp-asel")

        await c.post("/demo/reset")
    print("\nИТОГ:", "демо-сценарий проходит целиком ✅" if ok_all else "есть ошибки ❌")
    sys.exit(0 if ok_all else 1)


asyncio.run(main())
