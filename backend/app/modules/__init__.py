"""Модули приложения. Порядок важен для seed. Одна строка на модуль — при мерже только добавлять.

Владельцы — см. docs/OWNERSHIP.md: весь бэкенд — Даниил;
ext_* (каждый ext-модуль выключается флагом EXT_FEATURES).
"""

MODULES: list[str] = [
    "profile",
    "leave",
    "hr_question",
    "academy",
    "ai_jana",
]
