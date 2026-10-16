"""База знаний из app/seed/kb/<country>/*.md (frontmatter: title, source, updated)."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_jana.kb import invalidate
from app.modules.ai_jana.models import KbDoc
from app.seed.loader import SEED_DIR


def parse(md: str) -> tuple[dict[str, str], str]:
    meta: dict[str, str] = {}
    body = md
    if md.startswith("---"):
        _, front, body = md.split("---", 2)
        for line in front.strip().splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, body.strip()


async def seed(session: AsyncSession) -> None:
    for path in sorted((SEED_DIR / "kb").glob("*/*.md")):
        country = path.parent.name.upper()
        meta, body = parse(path.read_text(encoding="utf-8"))
        session.add(
            KbDoc(
                id=f"kb-{country.lower()}-{path.stem.replace('_', '-')}",
                country=country,
                title=meta["title"],
                source_label=meta["source"],
                body_md=body,
                status="published",
                updated_at=datetime.fromisoformat(meta["updated"]).replace(tzinfo=UTC),
            )
        )
    await session.flush()
    invalidate()
