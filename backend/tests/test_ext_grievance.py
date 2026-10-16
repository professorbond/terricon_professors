"""«Обращение» (CLAUDE.md §7.6)."""


async def submit(client, h, anonymous=True):
    r = await client.post("/api/ext/grievances", headers=h, json={"category": "manager", "text": "Руководитель смены повышает голос на сотрудников", "anonymous": anonymous})
    assert r.status_code == 201, r.text
    return r.json()


async def test_hr_gets_anonymous_grievance_without_author(client, login):
    ha, hd = await login("aigerim"), await login("daniyar")
    g = await submit(client, ha)
    assert g["employeeId"] == "emp-aigerim"  # автор видит своё
    for path in (f"/api/requests/{g['id']}", "/api/requests/inbox", "/api/requests/all", "/api/requests/all?type=grievance"):
        body = (await client.get(path, headers=hd)).json()
        items = body.get("items", [body])
        card = next(x for x in items if x["id"] == g["id"])
        assert card["employeeId"] is None and card["employeeName"] is None, path
        assert all(h["actorId"] is None and h["actorLabel"] == "Анонимный автор" for h in card["history"] if h["event"] == "created")
        assert "aigerim" not in str(card).lower() and "Айгерим" not in str(card)
    unit = (await client.get("/api/requests/all?unitId=kz-almaty-sc-b", headers=hd)).json()["items"]
    assert g["id"] not in {x["id"] for x in unit}


async def test_manager_cannot_see_grievances(client, login):
    g = await submit(client, await login("aigerim"), anonymous=False)
    he = await login("erlan")
    assert (await client.get(f"/api/requests/{g['id']}", headers=he)).status_code == 403
    assert g["id"] not in {x["id"] for x in (await client.get("/api/requests/inbox?status=all", headers=he)).json()["items"]}


async def test_grievance_has_deadline_and_hr_answers_with_reason(client, login):
    ha, hd = await login("aigerim"), await login("daniyar")
    g = await submit(client, ha)
    assert g["approverKind"] == "hr" and g["extensions"]["guarantee"]["resolution"] == "none"
    r = await client.post(f"/api/requests/{g['id']}/decide", headers=hd, json={"decision": "Approved"})
    assert r.json()["code"] == "COMMENT_REQUIRED"
    r = await client.post(f"/api/requests/{g['id']}/decide", headers=hd, json={"decision": "Approved", "comment": "Провели беседу с руководителем смены, ситуация на контроле HR."})
    assert r.status_code == 200
    note = next(n for n in (await client.get("/api/notifications", headers=ha)).json()["items"] if n["kind"] == "request.decided")
    assert note["title"] == "Ответ на обращение"


async def test_anonymous_overdue_grievance_not_in_radar_by_name(client, login):
    ha, hd = await login("asel"), await login("daniyar")
    await submit(client, ha, anonymous=True)
    await client.post("/api/demo/advance-time", json={"hours": 80})
    cards = {c["employeeId"]: c for c in (await client.get("/api/ext/hr/risks?country=KZ", headers=hd)).json()["items"]}
    assert "open_grievance" not in {s["kind"] for s in cards.get("emp-asel", {"signals": []})["signals"]}


async def test_named_overdue_grievance_in_radar(client, login):
    ha, hd = await login("asel"), await login("daniyar")
    await submit(client, ha, anonymous=False)
    await client.post("/api/demo/advance-time", json={"hours": 80})
    cards = {c["employeeId"]: c for c in (await client.get("/api/ext/hr/risks?country=KZ", headers=hd)).json()["items"]}
    assert "open_grievance" in {s["kind"] for s in cards["emp-asel"]["signals"]}
