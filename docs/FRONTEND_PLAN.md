# План встраивания экранов ext-фич во фронтенд напарника (часть Б, Б0)

Изучено состояние `feature` на 17.10.2026. Последние коммиты напарника — `0ed641e` «реализован фронт» и `6026e63` «добавлена анимация» от 16.10.

## Как устроен фронтенд

| Что | Где и как |
|---|---|
| Стек | React 19, TypeScript 6 (strict), Vite 8, Tailwind 4 и CSS-переменные, React Router 7, motion и GSAP, иконки lucide-react. Без TanStack Query и без UI-кита |
| Структура | `src/app` (провайдеры, роутер, каталог экранов), `layouts` (AppShell, меню), `pages`, `features/<домен>` (модели и компоненты), `components` (примитивы), `services` (контракты), `mocks` (адаптеры), `styles` |
| Роутер | `src/app/routes.ts` — каталог `plannedScreens` (путь, роли). `src/app/router.tsx` — `switch (screen.id)` в `DemoScreen` сопоставляет экран и компонент. Остальное показывается заглушкой `PlannedPage` |
| Меню | `src/layouts/navigation.ts` — `getNavigation(role)`: группы «Личное», «Команда», «HR» |
| UI-кит | Своих примитивов три: `components/ui/Button` (primary / secondary / quiet), `QueryState`, `WorkspaceHeading`. Плюс `components/motion/*` (SegmentedControl, AnimatedValue и др.). Остальное — классы в `styles/*.css` |
| Стили | Токены в `styles/tokens.css`: `--jana-green`, `--surface-*`, `--text-*`, `--status-*`. Дизайн-система JANA FLOW описана в `docs/DESIGN_SYSTEM.md` и `AGENTS.md`: типографика, без «AI-дашбордов», оранжевый — редкий акцент |
| i18n | **Нет.** Тексты на русском прямо в компонентах |
| Данные | `services/contracts.ts` — интерфейсы. `AppProviders` создаёт `createMockServices()` и кладёт в `ServicesContext`. Хук `useServiceQuery` подписан на ревизию мок-хранилища |
| **Вход и токен** | **Моки.** Вход — выбор роли (Employee / Manager / HRAdmin) в `sessionStorage`, данные в `localStorage` (`jana.mock-state.v1`). **HTTP-клиента и токена нет**, `services/http/` пуст |
| Экраны | Готовы: вход, главная (`pages/dashboard`), профиль (`pages/profile`), заявка на отпуск, «Мои заявки» и очередь руководителя (`pages/requests/RequestsPage`), карточка заявки (`RequestDetailPage`), окно решения (`features/leave/components/DecisionPanel`), уведомления. **Academy, AI Jana и все разделы HR — заглушки** `PlannedPage` |

## Точки подключения (план, по одному коммиту `touchpoint:`)

| Точка | Файл(ы) напарника | Возможно сейчас? |
|---|---|---|
| Маршрут | `src/app/routes.ts` (строка в каталоге) + `src/app/router.tsx` (ветка в `switch`) | ✅ |
| Пункт меню | `src/layouts/navigation.ts` | ✅ |
| Блок на главной | `src/pages/dashboard/DashboardPage.tsx` | ✅ |
| Блок в профиле | `src/pages/profile/ProfilePage.tsx` | ✅ |
| Бейдж в списке и карточке заявки | `src/features/leave/components/RequestList.tsx`, `src/pages/requests/RequestDetailPage.tsx` | ✅ |
| Поля причины в окне отказа | `src/features/leave/components/DecisionPanel.tsx` | ⚠️ Окно вызывает **мок** `services.leaveRequests.decide`, поэтому причина до бэкенда не дойдёт, пока нет HTTP-адаптера |
| Бейдж в Academy | — | ❌ Экрана Academy нет (заглушка) |
| Кнопка «Спросить HR» в AI-чате | — | ❌ Экрана AI Jana нет (заглушка) |

**Вне разрешённого списка** понадобится:
- статус «Передано HR» (`Escalated`): `src/features/leave/model.ts` (`LeaveStatus`) и `src/features/leave/presentation.ts` (подпись);
- без статуса `StatusBadge` упадёт на неизвестном значении.

## Что блокирует часть Б

1. **Нет настоящего входа и токена.** Мои экраны по правилу Б1 должны ходить в бэкенд с токеном из его авторизации, а токена нет.
   Если взять токен своим путём, его экраны покажут мок «Демо Сотрудник», а мои — Айгерим из бэкенда. Это две разные платформы на одном экране.
2. **Academy и AI-чат — заглушки.** Двум точкам подключения не во что встраиваться.
3. **Статус `Escalated`** — правка его модели, вне списка точек.
4. **i18n нет.** Требование «каждый экран RU/KZ» я могу выполнить только внутри своих модулей, со своим словарём. Переключатель языка в оболочке — тоже его файл.
