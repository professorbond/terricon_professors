"""HR-пульт: радар удержания + счётчик сохранённых денег (CLAUDE.md §7.5). Флаг: hr_console."""

from app.core.modules import BackendModule, ModuleContext
from app.modules.ext_hr_console.router import router
from app.modules.ext_hr_console.seed import seed
from app.modules.ext_hr_console.signals import recalculate

RU = {
    "risk.no_review": "{months} мес без пересмотра зарплаты",
    "risk.rejections": "{count} отказа по заявкам за полгода",
    "risk.pay_equity": "Новичку на {grade} предложили {offer} — больше текущего оклада ({salary})",
    "risk.slow_answers": "{count} заявки решены позже срока",
    "risk.open_grievance": "Вопрос {number} без ответа HR уже {days} дн.",
    "notif.salary_review.title": "Пересмотр зарплаты",
    "notif.salary_review.body": "HR назначил пересмотр вашей зарплаты на {date}",
}
KK = {
    "risk.no_review": "{months} ай жалақы қайта қаралмаған",
    "risk.rejections": "Жарты жылда {count} өтінімге бас тартылды",
    "risk.pay_equity": "{grade} бойынша жаңа қызметкерге {offer} ұсынылды — қазіргі жалақыдан ({salary}) көп",
    "risk.slow_answers": "{count} өтінім мерзімнен кеш шешілді",
    "risk.open_grievance": "{number} сұрағына HR {days} күн жауап бермеді",
    "notif.salary_review.title": "Жалақыны қайта қарау",
    "notif.salary_review.body": "HR жалақыңызды {date} қайта қарауды тағайындады",
}


def register(ctx: ModuleContext) -> None:
    ctx.i18n(RU, KK)
    ctx.ticks.register("ext_hr_console", recalculate)
    ctx.include_router(router)


module = BackendModule(name="ext_hr_console", feature="hr_console", register=register, seed=seed, description="HR-пульт")
