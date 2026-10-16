# Точки подключения во фронтенде напарника

Каждое изменение файла напарника — отдельный коммит с префиксом `touchpoint:`. Всё остальное лежит в моих
папках: `src/services/http/`, `src/modules/`. Его файлы не переформатированы, правки минимальные.

| # | Файл напарника | Что изменено | Зачем |
|---|---|---|---|
| 1 | `src/app/providers/AppProviders.tsx` | Выбор адаптера: `VITE_API_URL` задан → `createHttpServices`, иначе моки | Данные с бэкенда; без переменной его тесты на моках работают как раньше |
| 2 | `src/features/leave/model.ts`, `src/features/leave/presentation.ts` | `'Escalated'` в `LeaveStatus`, подпись «Передано HR», следующий шаг «Решение: HR» | Статус гарантий: срок руководителя истёк, заявка передана HR (разрешено Даниилом) |
| 3 | `src/app/routes.ts`, `src/app/router.tsx` | Каталог экранов дополняется `extPlannedScreens()`; в `DemoScreen` перед заглушкой — `extElement(screen.id)` | Маршруты ext-экранов, а также экраны Academy и AI Jana вместо заглушек `PlannedPage` |
| 4 | `src/layouts/navigation.ts` | `getNavigation(role)` = его группы + `extNavigation(role)`; тело функции переименовано в `baseNavigation` | Пункты меню ext-фич отдельной группой «Сервисы JanaМен» (по ролям и флагам) |
| 5 | `src/pages/dashboard/DashboardPage.tsx` | `<ExtSlot name="home.widgets" />` после блока «В движении» | Блоки «Мои гарантии», «Зарплата по факту» на главной |
| 6 | `src/pages/profile/ProfilePage.tsx` | `<ExtSlot name="profile.sections" />` после карточки профиля | «Открытая лестница» в профиле |
