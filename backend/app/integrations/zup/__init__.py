"""1С:ЗУП — только чтение. Сейчас mock на таблицах zup_*; настоящий 1С подключается
реализацией ZupPort (OData/HTTP-сервис 1С) без изменений в модулях. См. docs/ARCHITECTURE.md."""

from app.integrations.zup.port import HireOffer, HrAttrs, Salary, TimesheetEntry, ZupPort
from app.integrations.zup.mock import MockZup


def get_zup() -> ZupPort:
    return MockZup()


__all__ = ["HireOffer", "HrAttrs", "MockZup", "Salary", "TimesheetEntry", "ZupPort", "get_zup"]
