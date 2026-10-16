"""Модули приложения. Порядок важен для seed. Одна строка на модуль — при мерже только добавлять.

Владельцы — см. docs/OWNERSHIP.md: весь бэкенд — Даниил;
ext_* (каждый ext-модуль выключается флагом EXT_FEATURES).
"""

MODULES: list[str] = [
    # ext_guarantees раньше заявок: seed-заявки получают сроки и причины отказа по политикам
    "ext_guarantees",
    # ext_ladder раньше academy: сдача курса в seed уже видит грейды
    "ext_ladder",
    "profile",
    "leave",
    "hr_question",
    "academy",
    "ai_jana",
    "ext_wage",
    "ext_hr_console",
    "ext_grievance",
]
