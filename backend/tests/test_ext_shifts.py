"""Биржа смен, мини (CLAUDE.md §7.8)."""

from datetime import timedelta

from app.core import clock


async def my(client, h):
    return (await client.get("/api/ext/shifts/my", headers=h)).json()["items"]


async def available(client, h):
    return (await client.get("/api/ext/shifts/available", headers=h)).json()["items"]


async def test_demo_aigerim_gives_asel_takes(client, login):
    ha, hs, he = await login("aigerim"), await login("asel"), await login("erlan")
    first = (await my(client, ha))[0]
    r = await client.post(f"/api/ext/shifts/{first['id']}/offer", headers=ha)
    assert r.status_code == 200 and r.json()["status"] == "offered"
    offered = [s for s in await available(client, hs) if s["id"] == first["id"]]
    assert offered and offered[0]["payPreview"] == 12000
    r = await client.post(f"/api/ext/shifts/{first['id']}/take", headers=hs)  # одно нажатие
    assert r.status_code == 200 and r.json()["assigneeId"] == "emp-asel" and r.json()["status"] == "taken"
    assert first["id"] not in {s["id"] for s in await my(client, ha)}
    n_asel = next(n for n in (await client.get("/api/notifications", headers=hs)).json()["items"] if n["kind"] == "shift.taken")
    assert "+12000" in n_asel["message"].replace(" ", "")
    n_aig = next(n for n in (await client.get("/api/notifications", headers=ha)).json()["items"] if n["kind"] == "shift.given")
    assert "Асель" in n_aig["message"]
    # Руководитель видит обмен, но не согласует
    team = {s["id"]: s for s in (await client.get("/api/ext/shifts/team", headers=he)).json()["items"]}
    assert [e["event"] for e in team[first["id"]]["history"]] == ["offered", "taken"]


async def test_open_shift_one_click_plus_12000(client, login):
    hs = await login("asel")
    open_shift = next(s for s in await available(client, hs) if s["status"] == "open")
    assert open_shift["payPreview"] == 12000
    r = await client.post(f"/api/ext/shifts/{open_shift['id']}/take", headers=hs)
    assert r.status_code == 200 and r.json()["mine"] is True
    r = await client.post(f"/api/ext/shifts/{open_shift['id']}/take", headers=await login("aigerim"))
    assert r.status_code == 409 and r.json()["code"] == "SHIFT_NOT_AVAILABLE"


async def test_overlap_rejected(client, login):
    ha, hn, hs = await login("aigerim"), await login("nurlan"), await login("asel")
    # Дневная смена Айгерим (+1, 08–20) не пересекается с ночной Нурлана (+1, 20–08) — он может её взять
    first = (await my(client, ha))[0]
    await client.post(f"/api/ext/shifts/{first['id']}/offer", headers=ha)
    assert (await client.post(f"/api/ext/shifts/{first['id']}/take", headers=hn)).status_code == 200

    # Айгерим берёт открытую смену +2 10–18, после этого смена Асель +2 08–20 с ней пересекается
    asel_day2 = (await my(client, hs))[0]
    await client.post(f"/api/ext/shifts/{asel_day2['id']}/offer", headers=hs)
    body = {"date": asel_day2["date"], "startTime": "10:00", "endTime": "18:00", "payPreview": 9000}
    extra = (await client.post("/api/ext/shifts", headers=await login("erlan"), json=body)).json()
    await client.post(f"/api/ext/shifts/{extra['id']}/take", headers=ha)
    r = await client.post(f"/api/ext/shifts/{asel_day2['id']}/take", headers=ha)
    assert r.status_code == 422 and r.json()["code"] == "SHIFT_OVERLAP"
    assert asel_day2["id"] not in {s["id"] for s in await available(client, ha)}


async def test_qualification_mismatch(client, login):
    he, hs = await login("erlan"), await login("asel")
    day = str(clock.today() + timedelta(days=9))
    r = await client.post("/api/ext/shifts", headers=he, json={"date": day, "startTime": "08:00", "endTime": "20:00", "qualification": "forklift", "payPreview": 15000})
    assert r.status_code == 201
    r = await client.post(f"/api/ext/shifts/{r.json()['id']}/take", headers=hs)
    assert r.status_code == 422 and r.json()["code"] == "QUALIFICATION_MISMATCH"


async def test_past_and_other_center(client, login):
    he = await login("erlan")
    r = await client.post("/api/ext/shifts", headers=he, json={"date": str(clock.today() - timedelta(days=1)), "startTime": "08:00", "endTime": "20:00", "payPreview": 12000})
    assert r.status_code == 422 and r.json()["code"] == "SHIFT_IN_PAST"
    open_shift = next(s for s in await available(client, await login("asel")) if s["status"] == "open")
    r = await client.post(f"/api/ext/shifts/{open_shift['id']}/take", headers=await login("bakyt"))
    assert r.status_code == 403  # склад Бишкек ≠ СЦ Алматы
    # Смена в прошлом: переводим часы на 8 дней вперёд — открытая смена (+7) уже прошла
    await client.post("/api/demo/advance-time", json={"hours": 24 * 8})
    r = await client.post(f"/api/ext/shifts/{open_shift['id']}/take", headers=await login("asel"))
    assert r.status_code == 422 and r.json()["code"] == "SHIFT_IN_PAST"


async def test_permissions(client, login):
    ha = await login("aigerim")
    body = {"date": str(clock.today() + timedelta(days=3)), "startTime": "08:00", "endTime": "20:00", "payPreview": 1}
    assert (await client.post("/api/ext/shifts", headers=ha, json=body)).status_code == 403
    assert (await client.get("/api/ext/shifts/team", headers=ha)).status_code == 403
    asel_shift = (await my(client, await login("asel")))[0]
    assert (await client.post(f"/api/ext/shifts/{asel_shift['id']}/offer", headers=ha)).status_code == 403
    r = await client.post("/api/ext/shifts", headers=await login("gulnara"), json=body | {"centerId": "kg-bishkek-wh"})
    assert r.status_code == 403
    r = await client.post("/api/ext/shifts", headers=await login("daniyar"), json=body)
    assert r.json()["code"] == "CENTER_REQUIRED"
