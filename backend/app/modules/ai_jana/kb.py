"""Поиск по базе знаний: документы → чанки по заголовкам ## → BM25 только по стране пользователя.

Уверенность (confidence, 0..1) — доля «веса» значимых слов вопроса (IDF), найденных в лучшем фрагменте.
BM25 ранжирует, confidence решает, есть ли надёжный ответ (порог KB_MIN_SCORE)."""

import math
import re
from dataclasses import dataclass, field
from datetime import datetime

from rank_bm25 import BM25Okapi
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_jana.models import KbDoc
from app.modules.ai_jana.text import stem, terms, words

MAX_CHUNK = 800


@dataclass
class Chunk:
    doc_id: str
    title: str
    source_label: str
    section: str
    text: str
    updated_at: datetime
    terms: list[str] = field(default_factory=list)


@dataclass
class Hit:
    chunk: Chunk
    bm25: float
    confidence: float


def split_sections(body: str) -> list[tuple[str, str]]:
    """Режем по заголовкам ##; длинные разделы — по абзацам до ~800 символов."""
    parts: list[tuple[str, str]] = []
    for block in re.split(r"(?m)^##\s+", body):
        block = block.strip()
        if not block:
            continue
        heading, _, text = block.partition("\n")
        text = text.strip()
        buf = ""
        for para in re.split(r"\n\s*\n", text):
            if buf and len(buf) + len(para) > MAX_CHUNK:
                parts.append((heading.strip(), buf.strip()))
                buf = ""
            buf += para + "\n\n"
        if buf.strip():
            parts.append((heading.strip(), buf.strip()))
    return parts


class CountryIndex:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        corpus = [c.terms for c in chunks] or [[""]]
        self.bm25 = BM25Okapi(corpus)
        n = len(chunks)
        df: dict[str, int] = {}
        for c in chunks:
            for t in set(c.terms):
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        # Слово, которого нет в базе вообще, — самое «тяжёлое»: про это база ничего не знает
        self.unknown_idf = max(self.idf.values(), default=1.0) * 1.2

    def search(self, question: str, k: int = 3) -> list[Hit]:
        q = list(dict.fromkeys(terms(question)))
        if not q or not self.chunks:
            return []
        scores = self.bm25.get_scores(q)
        total = sum(self.idf.get(t, self.unknown_idf) for t in q)
        raw = {stem(w) for w in words(question)}
        candidates = sorted(range(len(self.chunks)), key=lambda i: scores[i], reverse=True)[: k * 3]
        hits = []
        for i in candidates:
            if scores[i] <= 0:
                continue
            c = self.chunks[i]
            present = set(c.terms) | set(terms(c.title + " " + c.section))
            covered = sum(self.idf.get(t, self.unknown_idf) for t in q if t in present)
            # Вторичный критерий: совпадение всех слов вопроса (вкл. служебные) — «сколько дней … положено»
            chunk_raw = {stem(w) for w in words(f"{c.section} {c.text}")}
            overlap = len(raw & chunk_raw) / len(raw) if raw else 0.0
            hits.append((covered / total if total else 0.0, overlap, float(scores[i]), c))
        hits.sort(key=lambda h: (round(h[0], 2), h[1], h[2]), reverse=True)
        return [Hit(c, bm, conf) for conf, _ov, bm, c in hits[:k]]


_cache: dict[str, tuple[tuple, CountryIndex]] = {}


async def index_for(session: AsyncSession, country: str) -> CountryIndex:
    """Индекс страны; пересобирается, если документы изменились (публикация нового правила)."""
    sig_row = (
        await session.execute(
            select(func.count(), func.max(KbDoc.updated_at)).where(KbDoc.country == country, KbDoc.status == "published")
        )
    ).one()
    sig = (sig_row[0], sig_row[1])
    cached = _cache.get(country)
    if cached and cached[0] == sig:
        return cached[1]
    docs = await session.scalars(select(KbDoc).where(KbDoc.country == country, KbDoc.status == "published"))
    chunks = []
    for d in docs:
        for section, text in split_sections(d.body_md):
            chunk = Chunk(d.id, d.title, d.source_label, section, text, d.updated_at)
            chunk.terms = terms(f"{d.title} {section} {text}")
            chunks.append(chunk)
    index = CountryIndex(chunks)
    _cache[country] = (sig, index)
    return index


def invalidate() -> None:
    _cache.clear()
