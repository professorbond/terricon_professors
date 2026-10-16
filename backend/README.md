# JanaМен · backend

FastAPI + SQLAlchemy 2 (async) + PostgreSQL 16 + Alembic. Python 3.12, зависимости через [uv](https://docs.astral.sh/uv/).

```sh
# из корня репозитория: всё сразу
docker compose up

# или локально
cd backend
uv sync
docker compose up -d db                       # Postgres на :5432
uv run uvicorn app.main:app --reload          # http://localhost:8000/docs
uv run pytest -q                              # тесты (SQLite в памяти)
```

При старте применяются миграции, а если база пустая, то и seed. Пароль у всех учёток `demo1234`.

- API и как подключить фронт: [../docs/EXTENSION_POINTS.md](../docs/EXTENSION_POINTS.md)
- Архитектура и места интеграций: [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)

```
app/
  main.py            # сборка: core-роутеры + модули из modules/__init__.py
  core/              # каркас: config, db, clock, auth, rbac, errors, events, ticks, i18n, modules
    org/             # страны, подразделения, сотрудники; /api/profile/me, /api/employees, /api/team
    requests/        # движок заявок: реестр типов, статусы, история, права, /api/requests/*
    notifications/   # /api/notifications
    demo/            # /api/demo/* (перевод времени, сброс, вход за персонажа)
  integrations/      # zup (1С, только чтение) · documentolog · bank · llm — сейчас mock
  modules/           # leave (эталон), дальше academy, ai_jana, ext_*
  seed/              # вымышленные тестовые данные (JSON)
alembic/             # миграции (одна голова)
tests/
```
