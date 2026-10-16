"""Рентген руководителей (CLAUDE.md §7.9)."""


async def test_hr_sees_all_erlan_on_top(client, login):
    items = (await client.get("/api/ext/hr/xray", headers=await login("daniyar"))).json()["items"]
    by = {m["managerId"]: m for m in items}
    assert items[0]["managerId"] == "emp-erlan" and by["emp-erlan"]["lateDecisions"] == 3
    assert by["emp-gulnara"]["lateDecisions"] == 0 and by["emp-gulnara"]["medianResponseHours"] < by["emp-erlan"]["medianResponseHours"]
    assert by["emp-erlan"]["rejectionShare"] > 0 and by["emp-erlan"]["teamAtRisk"] >= 2
    assert {m["managerId"] for m in items} == {"emp-erlan", "emp-gulnara", "emp-aibek"}
    kg = (await client.get("/api/ext/hr/xray?country=KG", headers=await login("daniyar"))).json()["items"]
    assert [m["managerId"] for m in kg] == ["emp-aibek"]


async def test_manager_sees_only_self_and_percentile(client, login):
    me = (await client.get("/api/ext/hr/xray/me", headers=await login("erlan"))).json()
    assert me["metrics"]["managerId"] == "emp-erlan" and me["lateRank"] == 1 and me["slowerThanPct"] == 100
    assert "Гульнара" not in str(me) and "emp-gulnara" not in str(me)
    assert (await client.get("/api/ext/hr/xray", headers=await login("erlan"))).status_code == 403


async def test_employee_forbidden(client, login):
    h = await login("aigerim")
    assert (await client.get("/api/ext/hr/xray", headers=h)).status_code == 403
    assert (await client.get("/api/ext/hr/xray/me", headers=h)).status_code == 403
