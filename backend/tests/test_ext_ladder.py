"""«Открытая лестница» (CLAUDE.md §7.4)."""


async def test_ladder_for_aigerim(client, login):
    lad = (await client.get("/api/ext/ladder/me", headers=await login("aigerim"))).json()
    assert lad["current"] == {"code": "SORT-1", "title": "Сортировщик", "bandMin": 230000, "bandMax": 270000, "currency": "KZT"}
    assert lad["next"]["code"] == "SORT-2" and (lad["next"]["bandMin"], lad["next"]["bandMax"]) == (275000, 320000)
    assert lad["raiseToNextMin"] == 35000  # 275 000 − её оклад 240 000
    courses = {c["courseId"]: c["done"] for c in lad["criteria"] if c["kind"] == "course"}
    assert courses == {"course-returns": True, "course-safety": False}
    assert lad["remainingCourses"] == 1 and lad["ready"] is False
    assert {c["kind"] for c in lad["criteria"]} == {"course", "months_in_grade", "no_incidents"}


async def test_employee_never_gets_other_grades(client, login):
    h = await login("aigerim")
    lad = (await client.get("/api/ext/ladder/me", headers=h)).json()
    codes = {lad["current"]["code"], lad["next"]["code"]}
    assert codes == {"SORT-1", "SORT-2"} and "LEAD-1" not in str(lad)
    assert (await client.get("/api/ext/ladder/grades", headers=h)).status_code == 403
    assert (await client.get("/api/ext/ladder/grades", headers=await login("erlan"))).status_code == 403
    tags = (await client.get("/api/ext/ladder/course-tags", headers=h)).json()
    assert all(g["bandMin"] == 0 and g["bandMax"] == 0 for t in tags for g in t["grades"])  # без вилок
    assert {t["courseId"] for t in tags} == {"course-returns", "course-safety"}
    # Лестница с окладом — только в своём профиле
    other = (await client.get("/api/employees/emp-aigerim", headers=await login("erlan"))).json()
    assert "ladder" not in other["extensions"]


async def test_progress_grows_after_course_and_notifies(client, login):
    h = await login("aigerim")
    before = (await client.get("/api/ext/ladder/me", headers=h)).json()["criteriaDone"]
    for lid in ("l-saf-2", "l-saf-3", "l-saf-4"):
        await client.post(f"/api/academy/lessons/{lid}/complete", headers=h)
    await client.post("/api/academy/courses/course-safety/submit", headers=h, json={"answers": [1, 1, 1, 0]})
    lad = (await client.get("/api/ext/ladder/me", headers=h)).json()
    assert lad["criteriaDone"] == before + 1 and lad["remainingCourses"] == 0 and lad["ready"] is True
    note = next(n for n in (await client.get("/api/notifications?unreadOnly=true", headers=h)).json()["items"] if n["kind"].startswith("ladder."))
    assert note["kind"] == "ladder.ready" and "Старший сортировщик" in note["message"]
    assert note["target"] == {"kind": "course", "courseId": "course-safety"}  # NotificationTarget фронтенда


async def test_nurlan_not_ready_due_to_incident(client, login):
    lad = (await client.get("/api/ext/ladder/me", headers=await login("nurlan"))).json()
    incidents = next(c for c in lad["criteria"] if c["kind"] == "no_incidents")
    assert incidents["done"] is False and incidents["actual"] == 3


async def test_next_review_date_moves_after_radar_proposal(client, login):
    ha, hd = await login("aigerim"), await login("daniyar")
    old = (await client.get("/api/ext/ladder/me", headers=ha)).json()["nextReviewDate"]
    cards = (await client.get("/api/ext/hr/risks?country=KZ", headers=hd)).json()["items"]
    sig = next(s for c in cards if c["employeeId"] == "emp-aigerim" for s in c["signals"] if s["kind"] == "no_review")
    await client.post(f"/api/ext/hr/risks/{sig['id']}/propose-review", headers=hd)
    new = (await client.get("/api/ext/ladder/me", headers=ha)).json()["nextReviewDate"]
    assert new != old and new > old


async def test_kg_ladder_and_hr_grades(client, login):
    lad = (await client.get("/api/ext/ladder/me", headers=await login("bakyt"))).json()
    assert lad["current"]["code"] == "KG-SORT-1" and lad["current"]["currency"] == "KGS"
    all_kz = (await client.get("/api/ext/ladder/grades?country=KZ", headers=await login("daniyar"))).json()
    assert [g["code"] for g in all_kz][:2] == ["SORT-1", "SORT-2"]
