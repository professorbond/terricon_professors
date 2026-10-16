from pydantic import Field

from app.core.schemas import ApiModel


class WageSummary(ApiModel):
    """«Доступно сейчас: 84 000 ₸ · Отработано 14 смен · заработано 168 000 ₸»."""

    period: str
    currency: str
    shifts_worked: int
    night_shifts: int
    shifts_planned: int
    earned: int
    limit_pct: int
    withdrawn: int
    available: int
    withdrawals_left: int
    min_amount: int
    max_per_period: int


class WithdrawIn(ApiModel):
    amount: int = Field(gt=0)


class WithdrawOut(ApiModel):
    request_id: str
    request_number: str
    amount: int
    document_number: str
    payout_id: str
    summary: WageSummary


class PayslipLine(ApiModel):
    code: str
    label: str
    amount: int  # положительное — начисление, отрицательное — удержание


class PayslipExplained(ApiModel):
    """Расчётка человеческим языком: смены + ночные − налоги = на руки; минус уже полученное по факту."""

    period: str
    currency: str
    lines: list[PayslipLine]
    gross: int
    net: int
    already_received: int
    to_be_paid: int
    note: str
