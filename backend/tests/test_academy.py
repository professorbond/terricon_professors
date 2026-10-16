"""Jana Academy (CLAUDE.md §5.4)."""

from app.core.events import events


async def test_my_courses_match_frontend_contract(client, login):
    items = (await client.get("/api/academy/my", headers=await login("aigerim"))).json()["items"]
    by_id = {c["id"]: c for c in items}
    assert set(by_id) == {"course-returns", "course-safety"}
    assert by_id["course-returns"]["progress"]["status"] == "Completed" and by_id["course-returns"]["progress"]["scorePercent"] == 100
    safety = by_id["course-safety"]
    assert {"id", "title", "description", "durationMinutes"} <= set(safety)
    assert safety["progress"] == {
        "courseId": "course-safety", "completedLessonIds": ["l-saf-1"], "totalLessons": 4,
        "status": "InProgress", "scorePercent": None, "passed": False, "lessonsPercent": 25,
    }


async def test_questions_without_correct_answers(client, login):
    body = (await client.get("/api/academy/courses/course-safety", headers=await login("aigerim"))).json()
    assert len(body["questions"]) == 4 and body["assigned"] is True
    for q in body["questions"]:
        assert set(q) == {"id", "ord", "text", "options"}
    assert "correct" not in str(body).lower()


async def test_pass_course_updates_profile_and_publishes_event(client, login):
    seen = []

    async def on_completed(session, employee, course, score):
        seen.append((employee.id, course.id, score))

    events.subscribe("academy.course_completed", on_completed)
    h = await login("aigerim")
    for lid in ("l-saf-2", "l-saf-3", "l-saf-4"):
        r = await client.post(f"/api/academy/lessons/{lid}/complete", headers=h)
    assert r.json()["lessonsPercent"] == 100 and r.json()["status"] == "InProgress"

    r = await client.post("/api/academy/courses/course-safety/submit", headers=h, json={"answers": [0, 1, 1, 0]})
    assert r.json()["passed"] is False and r.json()["score"] == 75 and seen == []
    r = await client.post("/api/academy/courses/course-safety/submit", headers=h, json={"answers": [1, 1, 1, 0]})
    assert r.json() | {"progress": None} == {"score": 100, "passed": True, "passingScore": 80, "correct": 4, "total": 4, "progress": None}
    assert r.json()["progress"]["status"] == "Completed"
    assert seen == [("emp-aigerim", "course-safety", 100)]

    profile = (await client.get("/api/profile/me", headers=h)).json()
    safety = next(t for t in profile["assignedTraining"] if t["courseId"] == "course-safety")
    assert safety["status"] == "Completed" and safety["scorePercent"] == 100
    note = (await client.get("/api/notifications?unreadOnly=true", headers=h)).json()["items"][0]
    assert note["kind"] == "academy.completed" and note["target"] == {"kind": "course", "courseId": "course-safety"}

    # Повторная сдача не публикует событие второй раз
    await client.post("/api/academy/courses/course-safety/submit", headers=h, json={"answers": [1, 1, 1, 0]})
    assert len(seen) == 1


async def test_submit_requires_all_answers(client, login):
    r = await client.post("/api/academy/courses/course-safety/submit", headers=await login("aigerim"), json={"answers": [1]})
    assert r.status_code == 422 and r.json()["code"] == "ANSWERS_MISMATCH"


async def test_assign_rules(client, login):
    he, hg, hd = await login("erlan"), await login("gulnara"), await login("daniyar")
    # Руководитель не может назначить курс чужой команде
    r = await client.post("/api/academy/assignments", headers=he, json={"employeeId": "emp-asel", "courseId": "course-safety"})
    assert r.status_code == 403
    # Сотрудник не назначает
    r = await client.post("/api/academy/assignments", headers=await login("aigerim"), json={"employeeId": "emp-nurlan", "courseId": "course-returns"})
    assert r.status_code == 403
    r = await client.post("/api/academy/assignments", headers=hg, json={"employeeId": "emp-asel", "courseId": "course-safety", "dueDate": "2099-01-01"})
    assert r.status_code == 201
    note = (await client.get("/api/notifications?unreadOnly=true", headers=await login("asel"))).json()["items"][0]
    assert note["kind"] == "academy.assigned" and "01.01.2099" in note["message"]
    r = await client.post("/api/academy/assignments", headers=hg, json={"employeeId": "emp-asel", "courseId": "course-safety"})
    assert r.status_code == 409 and r.json()["code"] == "ALREADY_ASSIGNED"
    # HR назначает кому угодно, в т.ч. в другой стране
    r = await client.post("/api/academy/assignments", headers=hd, json={"employeeId": "emp-bakyt", "courseId": "course-returns"})
    assert r.status_code == 201


async def test_progress_report_scoped(client, login):
    mine = (await client.get("/api/academy/progress", headers=await login("erlan"))).json()["items"]
    assert {r["employeeId"] for r in mine} == {"emp-aigerim", "emp-nurlan"}
    unit = (await client.get("/api/academy/progress?unitId=kz-almaty-sc-a", headers=await login("daniyar"))).json()["items"]
    assert {r["employeeId"] for r in unit} == {"emp-asel"}
    assert (await client.get("/api/academy/progress", headers=await login("aigerim"))).status_code == 403


async def test_catalog_and_unknown(client, login):
    h = await login("bakyt")
    assert len((await client.get("/api/academy/courses", headers=h)).json()["items"]) == 2
    assert (await client.get("/api/academy/courses/nope", headers=h)).status_code == 404
    assert (await client.post("/api/academy/lessons/nope/complete", headers=h)).status_code == 404


async def test_kazakh_course_titles(client, login):
    h = await login("aigerim")
    await client.put("/api/auth/me/lang", headers=h, json={"lang": "kk"})
    titles = {c["title"] for c in (await client.get("/api/academy/courses", headers=h)).json()["items"]}
    assert "Қайтарымдармен жұмыс" in titles
