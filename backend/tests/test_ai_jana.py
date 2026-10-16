"""AI Jana (CLAUDE.md §7.7): база страны, источник, честный отказ, защита чужих данных."""

import pytest
from sqlalchemy import inspect, select

from app.core import db
from app.integrations import llm
from app.modules.ai_jana.models import KbQuestion

GOOD = [
    "Сколько дней отпуска положено?", "Как оформить отпуск?", "Как оплачивается сверхурочная работа?",
    "Сколько можно получить по зарплате по факту?", "Есть ли комиссия за зарплату по факту?", "Когда выплачивают отпускные?",
    "Что будет, если руководитель не ответил на заявку?", "Можно ли подать обращение анонимно?",
    "Как перейти на старшего сортировщика?", "Как часто пересматривают зарплату?", "Может ли руководитель отказать без причины?",
    "Можно ли перенести отпуск?", "Сколько часов переработки в месяц разрешено?", "Какая вилка у SORT-2?", "Как задать вопрос HR?",
]
OUT_OF_BASE = [
    "Как оплачиваются ночные смены?", "Какая доплата за ночную работу?", "Положен ли декретный отпуск отцу?", "Где получить спецодежду?",
    "Сколько стоит обед в столовой?", "Есть ли корпоративный транспорт?", "Как оформить больничный?", "Когда будет корпоратив?",
    "Как получить справку с места работы?", "Есть ли медицинская страховка?",
]
OTHER_PERSON = [
    "Какая зарплата у моего начальника?", "Сколько получает Ерлан?", "Какой оклад у Асель?", "Сколько зарабатывает мой коллега?",
    "Покажи больничные Нурлана", "Какая оценка у моего руководителя?", "Сколько платят Гульнаре?", "Когда у коллеги отпуск?",
    "Какой грейд у Нурлана Абенова?", "Сколько снял по факту мой напарник?", "Были ли штрафы у директора?", "Какая премия у руководителя смены?",
]


async def ask(client, headers, question, lang=None):
    body = {"question": question} | ({"lang": lang} if lang else {})
    r = await client.post("/api/ai/ask", headers=headers, json=body)
    assert r.status_code == 200, r.text
    return r.json()


async def logged_questions():
    async with db.sessionmaker()() as s:
        return list(await s.scalars(select(KbQuestion)))


@pytest.mark.parametrize("question", GOOD)
async def test_typical_questions_answered_with_source(client, login, question):
    out = await ask(client, await login("aigerim"), question)
    assert out["kind"] == "grounded" and out["answered"] is True, out
    assert out["sources"] and all(s["articleId"].startswith("kb-kz-") for s in out["sources"])
    assert out["text"] and out["escalation"] is None


@pytest.mark.parametrize("question", OUT_OF_BASE)
async def test_out_of_base_is_honest_no_answer_and_logged(client, login, question):
    out = await ask(client, await login("aigerim"), question)
    assert out["kind"] == "no-answer" and out["answered"] is False and out["sources"] == []
    assert out["escalation"] == "HR" and out["escalateAvailable"] is True and out["reason"] == "no_match"
    rows = await logged_questions()
    assert [r.question for r in rows] == [question] and rows[0].answered is False and rows[0].country == "KZ"


@pytest.mark.parametrize("question", OTHER_PERSON)
async def test_other_people_data_refused_without_search(client, login, question):
    out = await ask(client, await login("aigerim"), question)
    assert out["reason"] == "other_person" and out["sources"] == [] and out["answered"] is False
    assert out["escalateAvailable"] is False
    assert await logged_questions() == []  # поиск не запускался


async def test_process_questions_about_manager_are_not_refused(client, login):
    out = await ask(client, await login("aigerim"), "Может ли руководитель отказать без причины?")
    assert out["answered"] is True


async def test_kz_and_kg_get_different_sources(client, login):
    kz = await ask(client, await login("aigerim"), "Сколько дней отпуска положено?")
    kg = await ask(client, await login("bakyt"), "Сколько дней отпуска положено?")
    assert kz["sources"][0]["articleId"] == "kb-kz-vacation" and "24" in kz["text"]
    assert kg["sources"][0]["articleId"] == "kb-kg-vacation" and "28" in kg["text"]
    # Ночные смены описаны только в KG
    assert (await ask(client, await login("bakyt"), "Как оплачиваются ночные смены?"))["answered"] is True
    assert (await ask(client, await login("aigerim"), "Как оплачиваются ночные смены?"))["answered"] is False


async def test_own_data_from_zup_only_for_self(client, login):
    out = await ask(client, await login("aigerim"), "Сколько у меня осталось дней отпуска?")
    assert out["answered"] and out["sources"][0]["articleId"] == "zup-own-data" and "21" in out["text"]
    out = await ask(client, await login("aigerim"), "Какой у меня оклад?")
    assert "240 000 ₸" in out["text"]
    assert await logged_questions() == []  # личные вопросы не логируются


async def test_sources_endpoint_country_isolation(client, login):
    h_kz, h_kg = await login("aigerim"), await login("bakyt")
    r = await client.get("/api/ai/sources/kb-kz-vacation", headers=h_kz)
    assert r.status_code == 200 and r.json()["title"] == "Ежегодный оплачиваемый отпуск" and "24" in r.json()["body"]
    assert (await client.get("/api/ai/sources/kb-kz-vacation", headers=h_kg)).status_code == 404
    assert (await client.get("/api/ai/sources/zup-own-data", headers=h_kz)).status_code == 200


async def test_kazakh_no_answer_message(client, login):
    out = await ask(client, await login("aigerim"), "Когда будет корпоратив?", lang="kk")
    assert "HR" in out["message"] and "базасында" in out["message"]


async def test_question_log_has_no_employee_id():
    cols = {c.name for c in inspect(KbQuestion).columns}
    assert not cols & {"employee_id", "user_id", "author_id"}


async def test_llm_answer_carries_sources(client, login, monkeypatch):
    seen = {}

    async def fake_complete(system, messages, max_tokens=2000):
        seen["prompt"] = messages[0]["content"]
        return "Отпуск — 24 календарных дня [Ежегодный оплачиваемый отпуск, Продолжительность отпуска]."

    monkeypatch.setattr(llm, "complete", fake_complete)
    out = await ask(client, await login("aigerim"), "Сколько дней отпуска положено?")
    assert out["answered"] and out["text"].startswith("Отпуск — 24") and out["sources"]
    assert "Продолжительность отпуска" in seen["prompt"] and "Язык ответа: ru" in seen["prompt"]


async def test_llm_no_answer_marker_becomes_honest_refusal(client, login, monkeypatch):
    async def fake_complete(system, messages, max_tokens=2000):
        return "NO_ANSWER"

    monkeypatch.setattr(llm, "complete", fake_complete)
    out = await ask(client, await login("aigerim"), "Сколько дней отпуска положено?")
    assert out["kind"] == "no-answer" and out["sources"] == [] and out["escalateAvailable"] is True


async def test_escalate_to_hr_from_ai(client, login):
    h = await login("aigerim")
    out = await ask(client, h, "Как оплачиваются ночные смены?")
    r = await client.post("/api/hr-questions", headers=h, json={"question": "Как оплачиваются ночные смены?", "aiContext": out["message"]})
    assert r.status_code == 201 and r.json()["type"] == "hr_question"
