"""Пробелы базы знаний (CLAUDE.md §7.10)."""

RULE = (
    "## Оплата ночных смен\nНочные смены (с 22:00 до 6:00) оплачиваются с доплатой 50% к ставке за смену. "
    "Доплата за ночные смены начисляется автоматически по табелю."
)


async def gaps(client, h):
    return (await client.get("/api/ext/kb/gaps?country=KZ", headers=h)).json()


async def test_seed_groups_similar_questions(client, login):
    items = await gaps(client, await login("daniyar"))
    assert [g["count"] for g in items] == [23, 6, 4]
    night = items[0]
    assert "ночн" in night["label"].lower() and len(night["samples"]) == 5
    assert all("ночн" in s.lower() for s in night["samples"])


async def test_no_employee_identifiers_in_api(client, login):
    body = str(await gaps(client, await login("daniyar")))
    for marker in ("emp-", "employeeId", "aigerim", "Айгерим"):
        assert marker not in body


async def test_new_unanswered_question_joins_group(client, login):
    await client.post("/api/ai/ask", headers=await login("aigerim"), json={"question": "Как оплачивается ночная смена?"})
    items = await gaps(client, await login("daniyar"))
    assert items[0]["count"] == 24


async def test_draft_edit_publish_then_ai_answers(client, login):
    hd, ha = await login("daniyar"), await login("aigerim")
    gap = (await gaps(client, hd))[0]
    assert (await client.post("/api/ai/ask", headers=ha, json={"question": "Как оплачиваются ночные смены?"})).json()["answered"] is False

    draft = (await client.post(f"/api/ext/kb/gaps/{gap['id']}/draft", headers=hd)).json()
    assert draft["status"] == "draft" and draft["body"] if "body" in draft else draft["bodyMd"].startswith("## ")
    # Черновик не виден AI, пока HR не опубликует
    assert (await client.post("/api/ai/ask", headers=ha, json={"question": "Как оплачиваются ночные смены?"})).json()["answered"] is False

    r = await client.put(f"/api/ext/kb/docs/{draft['id']}", headers=hd, json={"title": "Оплата ночных смен", "bodyMd": RULE})
    assert r.status_code == 200
    r = await client.post(f"/api/ext/kb/docs/{draft['id']}/publish", headers=hd)
    assert r.json()["status"] == "published"
    assert (await gaps(client, hd))[0]["status"] == "published"

    out = (await client.post("/api/ai/ask", headers=ha, json={"question": "Как оплачиваются ночные смены?"})).json()
    assert out["answered"] is True and out["sources"][0]["articleId"] == draft["id"]
    assert out["sources"][0]["sourceLabel"].startswith("Внутреннее правило")
    # KG эту базу не видит
    assert (await client.get(f"/api/ai/sources/{draft['id']}", headers=await login("bakyt"))).status_code == 404
    # Опубликованное больше не правится как черновик
    assert (await client.put(f"/api/ext/kb/docs/{draft['id']}", headers=hd, json={"bodyMd": RULE + " ещё"})).status_code == 409


async def test_hr_only(client, login):
    for who in ("aigerim", "erlan"):
        assert (await client.get("/api/ext/kb/gaps", headers=await login(who))).status_code == 403
