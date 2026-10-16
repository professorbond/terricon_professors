"""Защита до поиска (CLAUDE.md §7.7):
  - вопрос о данных ДРУГОГО человека (зарплата, больничный, оценка, отпуск коллеги/начальника) → отказ без поиска;
  - вопрос о СВОИХ данных («сколько у меня отпуска», «мой оклад») → ответ из 1С:ЗУП только для текущего пользователя.
Правила, без LLM: детерминированно и проверяемо тестами."""

import re
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.org.models import Employee
from app.modules.ai_jana.text import words

# Личные данные, которые нельзя раскрывать про других
SENSITIVE = re.compile(
    r"зарплат|оклад|получа|зарабат|плат(ят|ит|ишь)|преми|бонус|больнич|оценк|штраф|замечан|выговор|телефон|"
    r"адрес|возраст|грейд|ставк|уволь|увольн|рейтинг|kpi|кпи|аванс|по факту|сняли|снял"
)
# Указание на другого человека
OTHER_ROLE = re.compile(
    r"начальн|руководит|директор|менеджер|коллег|сосед|напарник|бригадир|сменщи|другого сотрудник|"
    r"других сотрудник|чужо|у него|у неё|у нее|его зарплат|её зарплат|ее зарплат|у них|у всех|каждого|"
    r"\bвсех\b|\bвсем\b|сотрудников|коллектив"
)
# «Кто на больничном / кто сколько получает / кого уволят» — вопрос о других людях, даже без имени.
# «Кто оплачивает больничный» — вопрос о правилах, его не трогаем.
WHO_OTHERS = re.compile(
    r"\bкто\b(\s+\w+)?\s+(на|в)\s+(больнич|отпуск|декрет)|\bкто\b.*\b(получа|зарабат)\w*\s+(больше|меньше|сколько)|"
    r"\bкто\b.*(уволь|штраф|выговор)|\bкого\b.*(уволь|сократ|штраф)"
)
# Про отпуск/больничный другого — только в форме «у <кого-то>»/«когда <кто-то> в отпуске»
OTHER_ABSENCE = re.compile(r"(отпуск|больнич).*(начальн|руководит|коллег|напарник|сменщи)|(начальн|руководит|коллег|напарник|сменщи).*(отпуск|больнич)")
# Вопрос о процессе, а не о данных человека: «как руководитель согласует», «сколько руководитель отвечает»
PROCESS = re.compile(r"соглас|отвеча|одобр|отклон|рассматр|срок ответа|подать|оформ|заявк")

OWN = re.compile(r"\bу меня\b|\bмой\b|\bмоя\b|\bмоё\b|\bмое\b|\bмои\b|\bмне\b|\bя\b|\bмоего\b|\bмоей\b")
OWN_VACATION = re.compile(r"отпуск|дней отдыха|остат")
OWN_SALARY = re.compile(r"зарплат|оклад|получаю|зарабатываю")
OWN_WAGE = re.compile(r"по факту|снять|вывести|получить сейчас|аванс")

Verdict = Literal["other_person", "own_vacation", "own_salary", "own_wage", "kb"]


async def _other_names(session: AsyncSession, user: Employee) -> list[str]:
    """Основы имён коллег (первые 4 буквы имени и фамилии), кроме самого пользователя."""
    rows = await session.scalars(select(Employee.full_name).where(Employee.id != user.id, Employee.active))
    stems: set[str] = set()
    for full in rows:
        for part in full.lower().replace("ё", "е").split():
            if len(part) >= 4:
                stems.add(part[:4])
    own = {p[:4] for p in user.full_name.lower().replace("ё", "е").split() if len(p) >= 4}
    return sorted(stems - own)


async def classify(session: AsyncSession, user: Employee, question: str) -> Verdict:
    q = " ".join(words(question))
    names = await _other_names(session, user)
    mentions_name = any(w[:4] in names for w in words(question) if len(w) >= 4)
    mentions_other = bool(OTHER_ROLE.search(q)) or mentions_name
    if mentions_other and SENSITIVE.search(q) and not (PROCESS.search(q) and not mentions_name):
        return "other_person"
    if mentions_name and OWN_VACATION.search(q):
        return "other_person"
    if OTHER_ABSENCE.search(q) and not PROCESS.search(q):
        return "other_person"
    if WHO_OTHERS.search(q):
        return "other_person"
    if OWN.search(q) and not mentions_other:
        if OWN_WAGE.search(q):
            return "own_wage"
        if OWN_SALARY.search(q):
            return "own_salary"
        if OWN_VACATION.search(q) and re.search(r"сколько|остал|остат|осталось|какой", q):
            return "own_vacation"
    return "kb"
