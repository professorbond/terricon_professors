"""Ответ AI Jana: защита → свои данные из 1С → поиск по базе страны → LLM строго по фрагментам
или экстрактивный ответ. Ответа без источника не бывает."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.events import events
from app.core.ids import new_id
from app.core.org.models import Employee
from app.core.profile import profile_registry
from app.integrations import llm
from app.integrations.zup import get_zup
from app.modules.ai_jana import guard
from app.modules.ai_jana.kb import Hit, index_for
from app.modules.ai_jana.models import KbQuestion
from app.modules.ai_jana.schemas import AskOut, KnowledgeSource

KB_MIN_SCORE = 0.5  # подобран на наборе вопросов (tests/test_ai_jana.py)
NO_ANSWER = "NO_ANSWER"
OWN_DATA_ID = "zup-own-data"

TEXTS = {
    "ru": {
        "no_answer": "Надёжной информации об этом в базе знаний нет. Могу передать вопрос в HR — нажмите «Спросить HR».",
        "other_person": "Я не могу рассказывать о данных других сотрудников: зарплате, больничных, оценках, отпусках. "
        "Спросите о своих данных или о правилах компании.",
        "own_vacation": "У вас {days} дн. отпуска (по данным 1С:ЗУП на {as_of} с учётом одобренных заявок). "
        "На рассмотрении: {pending} дн., можно запросить ещё {available} дн.",
        "own_salary": "Ваш оклад по данным 1С:ЗУП — {base} в месяц.",
        "own_wage": "Сейчас можно получить {available} (заработано {earned} за отработанные смены). Подробности — в разделе «Зарплата по факту».",
        "own_data_title": "Данные 1С:ЗУП",
        "own_data_section": "Ваш профиль",
        "source_hint": "Источник",
    },
    "kk": {
        "no_answer": "Бұл туралы білім базасында сенімді ақпарат жоқ. Сұрақты HR-ға жібере аламын — «HR-дан сұрау» батырмасын басыңыз.",
        "other_person": "Басқа қызметкерлердің деректері туралы (жалақы, ауру парағы, бағалау, демалыс) айта алмаймын. "
        "Өз деректеріңіз немесе компания ережелері туралы сұраңыз.",
        "own_vacation": "Сізде {days} күн демалыс бар (1С:ЗУП деректері бойынша, {as_of}). "
        "Қаралуда: {pending} күн, тағы {available} күн сұрауға болады.",
        "own_salary": "1С:ЗУП бойынша сіздің жалақыңыз — айына {base}.",
        "own_wage": "Қазір {available} алуға болады (жұмыс істеген ауысымдар үшін {earned}).",
        "own_data_title": "1С:ЗУП деректері",
        "own_data_section": "Сіздің профиліңіз",
        "source_hint": "Дереккөз",
    },
}

SYSTEM_PROMPT = """Ты — AI Jana, HR-ассистент компании Jana Post. Отвечаешь сотрудникам на вопросы о правилах работы.

Правила:
- Отвечай ТОЛЬКО на основе фрагментов базы знаний из сообщения пользователя. Не добавляй фактов, цифр и правил, которых нет во фрагментах, даже если знаешь их.
- Если во фрагментах нет ответа на вопрос, ответь ровно одним словом: NO_ANSWER
- После каждого утверждения указывай источник в квадратных скобках в формате [Название документа, раздел].
- Отвечай коротко: 1–3 предложения, без вступлений.
- Отвечай на языке, указанном в сообщении (ru — русский, kk — казахский). Названия источников оставляй как во фрагментах.
- Ты не принимаешь кадровых решений и не обещаешь их — только объясняешь правила."""


def money(amount: int, country: str) -> str:
    return f"{amount:,}".replace(",", " ") + (" сом" if country == "KG" else " ₸")


@dataclass
class Asked:
    out: AskOut
    question_id: str | None


def _source(hit: Hit) -> KnowledgeSource:
    c = hit.chunk
    return KnowledgeSource(article_id=c.doc_id, title=c.title, section=c.section, updated_at=c.updated_at, source_label=c.source_label)


def _own_source(lang: str) -> KnowledgeSource:
    t = TEXTS[lang]
    return KnowledgeSource(
        article_id=OWN_DATA_ID, title=t["own_data_title"], section=t["own_data_section"], updated_at=clock.now(), source_label="1С:ЗУП"
    )


def grounded(text: str, sources: list[KnowledgeSource]) -> AskOut:
    return AskOut(kind="grounded", text=text, message=None, sources=sources, escalation=None, answer=text, answered=True, escalate_available=False)


def no_answer(message: str, reason: str, escalate: bool = True) -> AskOut:
    return AskOut(
        kind="no-answer", text=None, message=message, sources=[], escalation="HR" if escalate else None,
        answer=message, answered=False, escalate_available=escalate, reason=reason,
    )


async def _own_data(session: AsyncSession, user: Employee, verdict: str, lang: str) -> AskOut | None:
    t = TEXTS[lang]
    if verdict == "own_vacation":
        bal = (await profile_registry.collect(session, user, user)).get("leave_balance")
        if bal is None:
            return None
        text = t["own_vacation"].format(days=bal.days, as_of=bal.as_of.strftime("%d.%m.%Y"), pending=bal.pending_days, available=bal.available_days)
        return grounded(text, [_own_source(lang)])
    if verdict == "own_salary":
        salary = await get_zup().get_salary(session, user.id)
        if salary is None:
            return None
        return grounded(t["own_salary"].format(base=money(salary.monthly_base, user.country)), [_own_source(lang)])
    if verdict == "own_wage":
        # Заполняет модуль «Зарплата по факту», если он включён
        wage = (await profile_registry.collect(session, user, user)).get("wage_access")
        if wage is None:
            return None
        text = t["own_wage"].format(available=money(wage.available, user.country), earned=money(wage.earned, user.country))
        return grounded(text, [_own_source(lang)])
    return None


def _fragments(hits: list[Hit]) -> str:
    return "\n\n".join(f"[{h.chunk.title}, {h.chunk.section}]\n{h.chunk.text}" for h in hits)


async def ask(session: AsyncSession, user: Employee, question: str, lang: str) -> Asked:
    t = TEXTS.get(lang, TEXTS["ru"])
    verdict = await guard.classify(session, user, question)
    if verdict == "other_person":
        return Asked(no_answer(t["other_person"], "other_person", escalate=False), None)
    if verdict != "kb":
        own = await _own_data(session, user, verdict, lang)
        if own is not None:
            return Asked(own, None)

    index = await index_for(session, user.country)
    hits = index.search(question)
    reliable = [h for h in hits if h.confidence >= KB_MIN_SCORE]
    top = max((h.confidence for h in hits), default=0.0)

    out: AskOut | None = None
    if reliable:
        best = reliable[0]
        used = [h for h in reliable if h.chunk.doc_id == best.chunk.doc_id or h.confidence >= best.confidence * 0.8][:3]
        prompt = f"Язык ответа: {lang}\n\nФрагменты базы знаний:\n{_fragments(used)}\n\nВопрос сотрудника: {question}"
        text = await llm.complete(SYSTEM_PROMPT, [{"role": "user", "content": prompt}])
        if text is None:  # экстрактивный режим: лучший фрагмент как есть
            out = grounded(best.chunk.text, [_source(best)])
        elif text.strip() != NO_ANSWER and NO_ANSWER not in text:
            out = grounded(text, [_source(h) for h in used])
    if out is None or not out.sources:  # ответа без источника не бывает
        out = no_answer(t["no_answer"], "no_match")

    q = KbQuestion(id=new_id(), country=user.country, question=question.strip(), answered=out.answered, top_score=round(top, 3), asked_at=clock.now())
    session.add(q)
    await session.flush()
    if not out.answered:
        await events.emit("ai.unanswered", session=session, question=q)
    return Asked(out, q.id)
