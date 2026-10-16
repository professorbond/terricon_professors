# JanaМен · JANA FLOW

Frontend внутренней HR-платформы. Этап 04: **JANA MOTION / SIGNAL & FLOW**.
Рабочий сценарий отпуска сохранён:
Employee → заявка → решение Manager → история и уведомление Employee.
Визуальный язык JANA FLOW и AppShell сохранены. Backend и безопасной серверной
авторизации нет; все данные вымышленные, операции выполняются mock-сервисами.

## Запуск

Node.js 22.12+ (проверено на 22.21.0), npm. Выполнять в `terricon_professors`:

```sh
npm ci
npm run dev
```

В Windows PowerShell при блокировке npm.ps1 использовать `npm.cmd ci` и
`npm.cmd run dev`; менять execution policy системы не требуется.
Открыть локальный URL из вывода Vite. Секреты, env-файл и сервер не нужны.

```sh
npm run typecheck  # TypeScript
npm run lint       # Oxlint
npm run check      # lint + TypeScript + production build
npm run test:e2e   # Playwright: Chrome, сценарии и скриншоты
npm run preview    # preview готового dist, после build
```

`npm run build` создаёт `dist/`. Для размещения SPA настроить fallback нефайловых
URL на `index.html`, чтобы прямой вход на вложенный маршрут работал.
Публикация в текущем этапе не выполнялась.

## Что подготовлено

- React 19, TypeScript 6 (strict), Vite 8; основа — официальный React TS scaffold.
- Tailwind CSS 4 через Vite-плагин, CSS custom properties, авторские примитивы.
- React Router 7: демо-вход, lazy AppShell и страницы рабочего сценария, 404.
- Motion for React: короткие переходы; GSAP/@gsap/react: scoped intro входа с cleanup.
- Lucide React; локальные Manrope Variable и IBM Plex Mono с кириллицей.
- Типизированные сервисы auth/profile/leave/notifications с единым mock-хранилищем.
- AppShell: sidebar, верхняя панель, меню профиля, счётчик непрочитанных уведомлений,
  мобильная нижняя навигация и modal sheet с focus trap.
- Ручная SVG-схема процессов: маршруты, станции, координатные подписи и узел «ВЫ».

На `/login` доступны три демонстрационные роли без пароля:

| Роль | Начальная область |
| --- | --- |
| Employee / Сотрудник | `/dashboard` |
| Manager / Руководитель | `/manager/approvals` |
| HRAdmin / HR / Админ | `/hr` |

Роль сохраняется в sessionStorage текущей вкладки; при запрете storage работает в
памяти до обновления. Меню профиля позволяет сменить роль или выйти. Это удобство
демо, а не доказательство личности или прав доступа. Настоящих аккаунтов, паролей,
токенов нет. Заявки, события и уведомления живут в localStorage `jana.mock-state.v1`
и переживают обновление страницы и смену роли. Academy, AI Jana и HR остаются
обозначенными заглушками внутри готовой оболочки. `/__foundation` доступен только в dev.

## Показ жюри

Living Route визуализирует сохранённое событие: прорисовка SVG, один сигнал,
отклик станции и карточка этапа. Отказ идёт по отдельной тёплой ветке. Станции
интерактивны и доступны с клавиатуры. Повторная навигация не проигрывает то же событие.
На мобильном маршрут вертикальный, при reduced motion показано конечное состояние.
Переходы страниц сохраняют AppShell; общий набор микровзаимодействий находится в
`src/components/motion`. Бизнес-сервисы, API и схема localStorage этим этапом не изменены.

1. Войти как **Сотрудник**. Кабинет показывает профиль и тестовый остаток 24 дня.
2. «Оформить отпуск» → выбрать будущий период → «Проверить заявку» → подтвердить
   отправку. Появятся UUID, номер `JL-год-0001`, статус и Jana Flow Map.
3. В меню профиля выбрать «Сменить демо-роль» → **Руководитель**. Открыть заявку
   в очереди и подтвердить согласование либо отклонение с непустой причиной.
4. Вернуться в роль **Сотрудник**: статус и маршрут обновлены, история содержит
   решение, колокольчик показывает новое уведомление. Обновить страницу — данные остаются.
5. В уведомлениях открыть связанную заявку или отметить событие прочитанным.

Сотрудник и руководитель могут работать в разных вкладках одного origin: роль
отдельная для каждой вкладки, бизнес-данные общие и обновляются через storage events.
Демо рассчитано на современный Chrome с Web Locks для согласованной записи вкладок.
Без Web Locks остаётся последовательная работа одной вкладки.

Тестовый расчёт: календарные дни включительно, без праздников, начислений и кадровых
норм. Начальный лимит 24, вычитаются только Approved; Submitted не резервирует дни.
Остаток повторно проверяется при решении. Прошлые/обратные/некорректные даты,
превышение лимита и пересечения активных периодов отклоняются mock-сервисом.
Для нового показа в отдельном профиле браузера данные начнутся с нуля. Чтобы явно
сбросить текущие тестовые заявки, удалить **только** ключ `jana.mock-state.v1` в DevTools
→ Application → Local Storage и обновить страницу. Это удалит все заявки данного демо.

## Структура

```text
docs/
  DESIGN_SYSTEM.md     # Палитра, типографика, сетка, motion
  SCREEN_MAP.md        # Роли, экраны, переходы и состояния
src/
  app/                # App, провайдеры, router, каталог маршрутов
  components/         # brand, ui, motion: общие примитивы
  features/           # identity, leave, academy, assistant, notifications
  layouts/            # AppShell, navigation, UserMenu, MobileNavigation
  pages/              # login, dashboard, profile, leave, requests, notifications и заглушки
  services/           # Контракты, DI-контекст, useServiceQuery; далее HTTP-адаптеры
  mocks/              # seed, store, services, runtime validation, demo-session
  lib/                # Точечная интеграция GSAP
  styles/             # CSS tokens, Tailwind bridge, fonts, motion
  main.tsx
public/
  favicon.svg
AGENTS.md             # Постоянные правила разработки
playwright.config.ts  # Локальный браузерный прогон
tests/                # Вход/оболочка, сквозной leave flow, бизнес-инварианты сервисов
```

UI → сервисный контракт → mock adapter; позже → HTTP adapter.
Будущий ASP.NET Core backend отвечает за авторизацию, заявки и PostgreSQL, а также
за адаптеры 1С:ЗУП и Documentolog. Браузер не соединяется с ними напрямую.
Подробнее: [сервисная граница](src/services/README.md).

## Решения и ограничения

Общая заглушка обслуживает будущие разделы. Role metadata управляет демо-навигацией,
а mock-сервис проверяет владельца, команду и версию заявки. Эти проверки не защищают
localStorage от изменения пользователем. HTTP, form/query/state libraries и UI kit
не добавлены; новых зависимостей на этом этапе нет.
Шрифты self-hosted; ключи API в frontend не допускаются. Лицензии шрифтов
содержатся в соответствующих пакетах Fontsource.

Context7 использован для проверки API. Playwright MCP и Figma MCP не подключены.
Браузерная проверка выполнена локальным Playwright Test в headless Chrome:
скриншоты login и shell при 1440/390 px, проверка переполнения также при 320/768 px,
ошибок JS/консоли, трёх ролей, refresh/logout, клавиатуры, mobile dialog, reduced motion,
неизвестных URL и несовместимой демо-роли. Добавлены полный отпускной сценарий,
отклонение с причиной, валидация дат и пересечений, фильтры/сортировка, сохранение
после reload, синхронизация вкладок, запрет чужого/повторного решения, устаревшая
версия и ошибки записи. Тесты сервисов также запускаются командой `test:e2e`.

Скриншоты генерируются в `artifacts/screenshots/` (не добавляются в Git):
`login-*`, `shell-*`, `navigation-390.png`, `leave-form-*`, `leave-created-*`,
`manager-queue-*`, `leave-approved-*` для ширин 1440 и 390 px.
Motion-проверки добавляют `signal-submitted-*`, `signal-approved-*`, `signal-rejected-*`,
`signal-notification-*`, `signal-mobile-390.png`. Замер интервалов кадров сохраняется
в `artifacts/performance/living-route.json`; это измерение headless Chrome с диагностикой,
а не обещание стабильных 60 FPS. Тесты проверяют движение по пути, отсутствие replay,
отказ записи без анимации успеха, reduced motion на лету, быстрые переходы и cleanup.
Playwright сам запускает и останавливает Vite на `127.0.0.1:4173`.
По умолчанию используется установленный Chrome. На машине без Chrome установить
Chromium через `npx playwright install chromium`, затем задать
`PLAYWRIGHT_CHANNEL=chromium` перед `npm run test:e2e` (в PowerShell:
`$env:PLAYWRIGHT_CHANNEL='chromium'`). Тесты не используют пользовательский профиль браузера.

Перед следующими задачами читать [AGENTS.md](AGENTS.md),
[дизайн-систему](docs/DESIGN_SYSTEM.md) и [карту экранов](docs/SCREEN_MAP.md).
Основания: [Vite](https://vite.dev/guide/),
[Tailwind CSS](https://tailwindcss.com/docs/installation/using-vite),
[React Router](https://reactrouter.com/start/declarative/routing),
[Motion](https://motion.dev/docs/react-accessibility), [GSAP](https://gsap.com/resources/React/).
