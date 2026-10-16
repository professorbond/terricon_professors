"""«Зарплата по факту» (CLAUDE.md §7.3)."""

from app.core import clock


async def test_summary_matches_demo_numbers(client, login):
    s = (await client.get("/api/ext/wage/summary", headers=await login("aigerim"))).json()
    shifts = min(14, (clock.today() - clock.today().replace(day=1)).days)
    assert s["shiftsWorked"] == shifts and s["earned"] == shifts * 12000
    assert s["limitPct"] == 50 and s["available"] == shifts * 12000 // 2
    if shifts == 14:  # демо-день: 168 000 заработано → 84 000 доступно
        assert (s["earned"], s["available"]) == (168000, 84000)


async def test_kg_limit_is_40(client, login):
    s = (await client.get("/api/ext/wage/summary", headers=await login("bakyt"))).json()
    assert s["limitPct"] == 40 and s["currency"] == "KGS"
    assert s["earned"] == s["shiftsWorked"] * 1800 + s["nightShifts"] * 300


async def test_amount_exceeds_available(client, login):
    h = await login("aigerim")
    available = (await client.get("/api/ext/wage/summary", headers=h)).json()["available"]
    r = await client.post("/api/ext/wage/withdraw", headers=h, json={"amount": available + 1})
    assert r.status_code == 422 and r.json()["code"] == "AMOUNT_EXCEEDS_AVAILABLE" and r.json()["data"]["available"] == available
    r = await client.post("/api/ext/wage/withdraw", headers=h, json={"amount": 1000})
    assert r.json()["code"] == "BELOW_MIN_AMOUNT"


async def test_withdraw_creates_request_document_payout_notification(client, login):
    h = await login("aigerim")
    before = (await client.get("/api/ext/wage/summary", headers=h)).json()
    r = await client.post("/api/ext/wage/withdraw", headers=h, json={"amount": 30000})
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["summary"]["available"] == before["available"] - 30000 and out["summary"]["withdrawalsLeft"] == 1
    assert out["documentNumber"].startswith("DL-") and out["payoutId"]

    req = (await client.get(f"/api/requests/{out['requestId']}", headers=h)).json()
    assert req["type"] == "wage_access" and req["status"] == "Approved" and req["decidedBySystem"] is True
    assert req["typeTitle"] == "Зарплата по факту" and req["documents"][0]["kind"] == "wage_advance"
    assert [e["event"] for e in req["history"]] == ["created", "approved", "document_registered", "payout_sent"]
    mine = (await client.get("/api/requests/my?type=wage_access", headers=h)).json()["items"]
    assert [m["id"] for m in mine] == [out["requestId"]]
    note = next(n for n in (await client.get("/api/notifications", headers=h)).json()["items"] if n["kind"] == "wage.paid")
    assert note["title"] == "Деньги отправлены" and "30 000 ₸" in note["message"]
    # Руководитель в выводе не участвует и его не видит во входящих
    inbox = (await client.get("/api/requests/inbox?status=all", headers=await login("erlan"))).json()["items"]
    assert out["requestId"] not in {i["id"] for i in inbox}


async def test_limit_per_period(client, login):
    h = await login("aigerim")
    for _ in range(2):
        assert (await client.post("/api/ext/wage/withdraw", headers=h, json={"amount": 5000})).status_code == 201
    r = await client.post("/api/ext/wage/withdraw", headers=h, json={"amount": 5000})
    assert r.status_code == 422 and r.json()["code"] == "LIMIT_PER_PERIOD"


async def test_payslip_explained(client, login):
    h = await login("aigerim")
    await client.post("/api/ext/wage/withdraw", headers=h, json={"amount": 20000})
    p = (await client.get("/api/ext/wage/payslip-explained", headers=h)).json()
    codes = [line["code"] for line in p["lines"]]
    assert codes[0] == "SHIFTS" and {"OPV", "VOSMS", "IPN"} <= set(codes)
    assert p["net"] == p["gross"] + sum(line["amount"] for line in p["lines"] if line["amount"] < 0)
    assert p["alreadyReceived"] == 20000 and p["toBePaid"] == p["net"] - 20000
    assert "будет учтено в день зарплаты" in p["note"]
    assert (await client.get("/api/ext/wage/payslip-explained?period=2026-13", headers=h)).status_code == 422


async def test_profile_and_ai_see_own_wage(client, login):
    h = await login("aigerim")
    prof = (await client.get("/api/profile/me", headers=h)).json()
    assert prof["extensions"]["wageAccess"]["limitPct"] == 50
    other = (await client.get("/api/employees/emp-aigerim", headers=await login("erlan"))).json()
    assert "wageAccess" not in other["extensions"]  # руководитель не видит
    out = (await client.post("/api/ai/ask", headers=h, json={"question": "Сколько я могу снять по факту?"})).json()
    assert out["answered"] and out["sources"][0]["articleId"] == "zup-own-data"


async def test_feature_flag_off_hides_routes():
    from app.core.config import Settings
    from app.main import create_app

    app = create_app(Settings(ext_features="guarantees", auto_migrate=False, auto_seed=False, tick_interval_seconds=0))
    paths = set(app.openapi()["paths"])
    assert "/api/ext/wage/summary" not in paths and "/api/ext/policies" in paths
    create_app()  # вернуть реестры к полному набору модулей
