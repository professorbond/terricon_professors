"""Группировка вопросов без ответа: основы слов (стемминг) + TF-IDF + косинусная близость ≥ 0.5.
Сравниваются «темы пробела» — слова вопроса, которых нет в базе знаний страны."""

import math
from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ids import new_id
from app.modules.ai_jana import public as ai
from app.modules.ext_kb_gaps.models import KbGapGroup

THRESHOLD = 0.5


def _vector(tokens: list[str], idf: dict[str, float]) -> dict[str, float]:
    tf = Counter(tokens)
    vec = {t: c * idf.get(t, 1.0) for t, c in tf.items()}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {t: v / norm for t, v in vec.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(v * b.get(t, 0.0) for t, v in a.items())


async def assign(session: AsyncSession, question: ai.KbQuestion) -> KbGapGroup:
    """Отнести вопрос к самой близкой группе страны или открыть новую.

    IDF считается по базе знаний страны (+ сам вопрос): слова, которых нет в базе («ночные», «больничный»),
    весят больше всего — это и есть тема пробела. Близость — максимум из косинуса к центру группы
    и к ближайшему вопросу в ней."""
    groups = list(
        await session.scalars(select(KbGapGroup).where(KbGapGroup.country == question.country, KbGapGroup.status != "published"))
    )
    members = {g.id: await ai.group_questions(session, g.id) for g in groups}
    corpus = await ai.kb_corpus(session, question.country)
    # Вопросы группы в фон не входят: иначе частое слово темы («ночн») теряет вес
    docs = corpus + [ai.terms(question.question)]
    n = len(docs)
    df = Counter(t for d in docs for t in set(d))
    idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
    covered = {t for d in corpus for t in d}

    def topic(text: str) -> list[str]:
        # Тема пробела — слова, которых нет в базе; если все слова база знает — берём все
        tokens = ai.terms(text)
        return [t for t in tokens if t not in covered] or tokens

    target = _vector(topic(question.question), idf)

    best, best_score = None, 0.0
    for g in groups:
        vectors = [_vector(topic(q.question), idf) for q in members[g.id]]
        centroid: Counter[str] = Counter()
        for v in vectors:
            centroid.update(v)
        norm = math.sqrt(sum(v * v for v in centroid.values())) or 1.0
        score = max([cosine(target, {t: v / norm for t, v in centroid.items()})] + [cosine(target, v) for v in vectors])
        if score > best_score:
            best, best_score = g, score

    if best is None or best_score < THRESHOLD:
        best = KbGapGroup(
            id=new_id(), country=question.country, label=question.question, question_count=0,
            created_at=question.asked_at, last_asked_at=question.asked_at,
        )
        session.add(best)
        await session.flush()
    best.question_count += 1
    best.last_asked_at = max(best.last_asked_at, question.asked_at)
    # Метка — самая короткая формулировка (читается как тема)
    if len(question.question) < len(best.label):
        best.label = question.question
    await ai.set_group(session, question, best.id)
    return best
