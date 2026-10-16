"""AI Jana: тестовый набор из docs/AI_TEST_SET.md (20 вопросов)."""

import re
from pathlib import Path

import pytest

ROWS = [
    [c.strip() for c in line.strip().strip("|").split("|")]
    for line in (Path(__file__).resolve().parents[2] / "docs/AI_TEST_SET.md").read_text(encoding="utf-8").splitlines()
    if re.match(r"\|\s*\d+\s*\|", line)
]


def test_set_has_20_questions():
    assert len(ROWS) == 20


@pytest.mark.parametrize("num,who,question,expect,source", ROWS, ids=[r[0] for r in ROWS])
async def test_ai_question(client, login, num, who, question, expect, source):
    out = (await client.post("/api/ai/ask", headers=await login(who), json={"question": question})).json()
    if expect in ("answer", "own"):
        assert out["answered"] and out["sources"], (num, out)
        assert out["sources"][0]["articleId"].startswith(source), (num, out["sources"])
    elif expect == "refuse_other":
        assert out["reason"] == "other_person" and not out["sources"] and out["escalateAvailable"] is False, (num, out)
    else:
        assert not out["answered"] and not out["sources"] and out["escalateAvailable"] is True, (num, out)


@pytest.mark.parametrize(
    "question",
    ["Кто оплачивает больничный?", "Какой список документов нужен для больничного?", "Кто согласует мой отпуск?", "Сколько сотрудников может уйти в отпуск одновременно?"],
)
async def test_rule_questions_are_not_refused_as_other_person(client, login, question):
    """Ложные срабатывания защиты: вопросы о правилах не должны получать отказ «чужие данные»."""
    out = (await client.post("/api/ai/ask", headers=await login("aigerim"), json={"question": question})).json()
    assert out.get("reason") != "other_person", (question, out)
