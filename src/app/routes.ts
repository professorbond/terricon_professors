import type { Role } from '@/features/identity/model'
import { extPlannedScreens } from '@/modules'

export interface PlannedScreen {
  readonly id: string
  readonly path: string
  readonly title: string
  /** Product specification only. These values DO NOT enforce authorization. */
  readonly roles: readonly Role[]
}

const allRoles = ['Employee', 'Manager', 'HRAdmin'] as const

/** Screen catalogue. Leave flow is implemented; other business areas remain placeholders. */
const baseScreens = [
  { id: 'login', path: '/login', title: 'Вход в JanaМен', roles: [] },
  { id: 'dashboard', path: '/dashboard', title: 'Личный кабинет', roles: allRoles },
  { id: 'profile', path: '/profile', title: 'Профиль сотрудника', roles: allRoles },
  { id: 'requests', path: '/requests', title: 'Мои заявки', roles: allRoles },
  { id: 'leave-new', path: '/requests/new/leave', title: 'Заявка на отпуск', roles: allRoles },
  { id: 'request', path: '/requests/:requestId', title: 'История заявки', roles: allRoles },
  { id: 'notifications', path: '/notifications', title: 'Уведомления', roles: allRoles },
  { id: 'academy', path: '/academy', title: 'Jana Academy', roles: allRoles },
  { id: 'course', path: '/academy/:courseId', title: 'Учебный курс', roles: allRoles },
  { id: 'lesson', path: '/academy/:courseId/lessons/:lessonId', title: 'Материал курса', roles: allRoles },
  { id: 'result', path: '/academy/:courseId/result', title: 'Результат обучения', roles: allRoles },
  { id: 'assistant', path: '/ai-jana', title: 'AI Jana', roles: allRoles },
  { id: 'source', path: '/knowledge/:articleId', title: 'Источник ответа', roles: allRoles },
  { id: 'team', path: '/manager/team', title: 'Моя команда', roles: ['Manager'] },
  { id: 'approvals', path: '/manager/approvals', title: 'Согласование заявок', roles: ['Manager'] },
  { id: 'approval', path: '/manager/approvals/:requestId', title: 'Решение по заявке', roles: ['Manager'] },
  { id: 'hr', path: '/hr', title: 'Рабочее пространство HR', roles: ['HRAdmin'] },
  { id: 'hr-requests', path: '/hr/requests', title: 'Реестр заявок', roles: ['HRAdmin'] },
  { id: 'hr-request', path: '/hr/requests/:requestId', title: 'Обработка заявки', roles: ['HRAdmin'] },
  { id: 'hr-employees', path: '/hr/employees', title: 'Сотрудники', roles: ['HRAdmin'] },
  { id: 'hr-learning', path: '/hr/learning', title: 'Назначение обучения', roles: ['HRAdmin'] },
  { id: 'hr-knowledge', path: '/hr/knowledge', title: 'База знаний HR', roles: ['HRAdmin'] },
  { id: 'forbidden', path: '/forbidden', title: 'Доступ ограничен', roles: [] },
] as const satisfies readonly PlannedScreen[]

/** + экраны ext-фич (src/modules), только при работе с реальным API. */
export const plannedScreens: readonly PlannedScreen[] = [...baseScreens, ...extPlannedScreens()]
