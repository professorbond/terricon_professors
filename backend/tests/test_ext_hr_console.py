"""HR-пульт: радар удержания + счётчик (CLAUDE.md §7.5)."""

import pathlib


async def radar(client, h):
    return {c["employeeId"]: c for c in (await client.get("/api/ext/hr/risks?country=KZ", headers=h)).json()["items"]}


async def test_seed_has_three_people_with_different_reasons(client, login):
    cards = await radar(client, await login("daniyar"))
    kinds = {eid: {s["kind"] for s in c["signals"]} for eid, c in cards.items()}
    assert {"no_review", "pay_equity"} <= kinds["emp-aigerim"]
    assert {"rejections", "slow_answers", "open_grievance"} <= kinds["emp-nurlan"]
    assert "pay_equity" in kinds["emp-asel"]
    assert len({k for ks in kinds.values() for k in ks}) == 5
    aigerim = cards["emp-aigerim"]["signals"]
    titles = {s["kind"]: s["title"] for s in aigerim}
    assert titles["no_review"] == "14 мес без пересмотра зарплаты"
    assert "260 000 ₸" in titles["pay_equity"] and "240 000 ₸" in titles["pay_equity"]


async def test_employee_and_manager_forbidden(client, login):
    for who in ("aigerim", "erlan"):
        h = await login(who)
        assert (await client.get("/api/ext/hr/risks", headers=h)).status_code == 403
        assert (await client.get("/api/ext/hr/savings", headers=h)).status_code == 403


async def test_module_does_not_read_wage_or_ai_data():
    src = "".join(p.read_text() for p in pathlib.Path("app/modules/ext_hr_console").glob("*.py"))
    for forbidden in ("ext_wage", "Withdrawal", "ai_jana", "KbQuestion", "kb_questions", "wage_withdrawals"):
        assert forbidden not in src, forbidden


async def test_propose_review_notifies_and_sets_date(client, login):
    hd = await login("daniyar")
    signal = next(s for s in (await radar(client, hd))["emp-aigerim"]["signals"] if s["kind"] == "no_review")
    r = await client.post(f"/api/ext/hr/risks/{signal['id']}/propose-review", headers=hd)
    assert r.status_code == 200 and r.json()["nextReviewDate"] is not None
    assert next(s for s in r.json()["signals"] if s["id"] == signal["id"])["status"] == "actioned"
    note = (await client.get("/api/notifications?unreadOnly=true", headers=await login("aigerim"))).json()["items"][0]
    assert note["kind"] == "salary.review" and "пересмотр" in note["message"]
    # Пересчёт не открывает no_review заново: пересмотр уже предложен
    await client.post("/api/ext/hr/risks/recalculate", headers=hd)
    kinds = {s["kind"]: s["status"] for s in (await radar(client, hd))["emp-aigerim"]["signals"]}
    assert kinds["no_review"] == "actioned"


async def test_savings_counter_9_9_to_10_8(client, login):
    hd = await login("daniyar")
    s = (await client.get("/api/ext/hr/savings", headers=hd)).json()
    assert (s["retainedCount"], s["perPerson"], s["saved"]) == (11, 900000, 9_900_000)
    signal = (await radar(client, hd))["emp-aigerim"]["signals"][0]
    await client.post(f"/api/ext/hr/risks/{signal['id']}/confirm-retained", headers=hd)
    s = (await client.get("/api/ext/hr/savings", headers=hd)).json()
    assert s["saved"] == 10_800_000 and "12 ×" in s["formula"]


async def test_signal_resolves_when_cause_disappears(client, login):
    hd, hn = await login("daniyar"), await login("nurlan")
    q = next(r for r in (await client.get("/api/requests/my?type=hr_question", headers=hn)).json()["items"])
    await client.post(f"/api/requests/{q['id']}/decide", headers=hd, json={"decision": "Approved", "comment": "Ночные — по ст. 110 ТК РК, +50%."})
    await client.post("/api/ext/hr/risks/recalculate", headers=hd)
    kinds = {s["kind"] for s in (await radar(client, hd))["emp-nurlan"]["signals"]}
    assert "open_grievance" not in kinds and "rejections" in kinds


async def test_tick_detects_new_signals(client, login):
    """Новый оффер выше оклада → после тика у сотрудника сигнал pay_equity (KG пока чистый)."""
    hd = await login("daniyar")
    assert (await client.get("/api/ext/hr/risks?country=KG", headers=hd)).json()["items"] == []
    from app.core import clock, db
    from app.integrations.zup.models import ZupHireOffer

    async with db.sessionmaker()() as s:
        s.add(ZupHireOffer(id="offer-kg", position="Сортировщик", grade_code="KG-SORT-1", country="KG", offered_monthly_base=40000, offered_at=clock.now()))
        await s.commit()
    await client.post("/api/demo/advance-time", json={"hours": 1})
    kg = (await client.get("/api/ext/hr/risks?country=KG", headers=hd)).json()["items"]
    assert [c["employeeId"] for c in kg] == ["emp-bakyt"] and kg[0]["signals"][0]["kind"] == "pay_equity"
