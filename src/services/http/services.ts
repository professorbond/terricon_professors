import type { ApplicationServices, Page, ServiceResult } from '../contracts'
import type { DemoSessionStore } from '../demo-session'
import type { EmployeeProfile, Role, User } from '@/features/identity/model'
import type { LeaveRequest } from '@/features/leave/model'
import type { EmployeeNotification } from '@/features/notifications/model'
import { api, revisionStore, tokenStore } from './client'

interface LoginOut { accessToken: string; user: User }

/** В историю заявки напарника — только смены статуса. Служебные отметки бэкенда
 * (срок ответа, приказ в Documentolog) показывают ext-бейджи, а не его таймлайн. */
const STATUS_EVENTS = new Set(['created', 'approved', 'rejected', 'escalated', 'cancelled'])
type ApiEvent = LeaveRequest['history'][number] & { readonly event?: string }
type ApiLeave = Omit<LeaveRequest, 'history'> & { readonly history: readonly ApiEvent[] }
const toLeave = (request: ApiLeave): LeaveRequest => ({ ...request, history: request.history.filter((item) => !item.event || STATUS_EVENTS.has(item.event)) })
const mapOne = (result: ServiceResult<ApiLeave>): ServiceResult<LeaveRequest> => (result.ok ? { ok: true, data: toLeave(result.data) } : result)
const mapPage = (result: ServiceResult<Page<ApiLeave>>): ServiceResult<Page<LeaveRequest>> => (result.ok ? { ok: true, data: { ...result.data, items: result.data.items.map(toLeave) } } : result)

/** Реальные сервисы поверх API бэкенда (docs/API_CONTRACT.md). Те же контракты, что и у mock-адаптера. */
export function createHttpServices(session: DemoSessionStore): ApplicationServices {
  async function signIn(body: { role: Role } | { login: string }): Promise<ServiceResult<User>> {
    const result = await api.post<LoginOut>('/demo/login-as', body)
    if (!result.ok) return result
    tokenStore.write(result.data.accessToken)
    session.writeRole(result.data.user.role)
    revisionStore.bump()
    return { ok: true, data: result.data.user }
  }

  return {
    subscribe: revisionStore.subscribe,
    getRevision: revisionStore.getRevision,
    auth: {
      async getCurrentUser() {
        if (!tokenStore.read()) { session.writeRole(null); return { ok: true, data: null } }
        const result = await api.get<User>('/auth/me')
        if (!result.ok && result.problem.kind === 'unauthenticated') { session.writeRole(null); return { ok: true, data: null } }
        if (result.ok) session.writeRole(result.data.role)
        return result
      },
      signInDemo: (role) => signIn({ role }),
      async signOut() { tokenStore.write(null); session.writeRole(null); revisionStore.bump(); return { ok: true, data: null } },
    },
    profiles: { getMyProfile: (options) => api.get<EmployeeProfile>('/profile/me', options) },
    leaveRequests: {
      listMine: async (options) => mapPage(await api.get<Page<ApiLeave>>('/leave/my', options)),
      listTeam: async (options) => mapPage(await api.get<Page<ApiLeave>>('/leave/team', options)),
      listPendingApprovals: async (options) => mapPage(await api.get<Page<ApiLeave>>('/leave/pending', options)),
      getById: async (id, options) => mapOne(await api.get<ApiLeave>(`/leave/${encodeURIComponent(id)}`, options)),
      submit: async (input, options) => mapOne(await api.post<ApiLeave>('/leave', input, options)),
      decide: async (id, input, options) => mapOne(await api.post<ApiLeave>(`/leave/${encodeURIComponent(id)}/decision`, input, options)),
    },
    notifications: {
      listMine: (options) => api.get<Page<EmployeeNotification>>('/notifications', options),
      markRead: (id, options) => api.post<EmployeeNotification>(`/notifications/${encodeURIComponent(id)}/read`, undefined, options),
    },
  }
}

/** Вход за конкретного персонажа seed (демо-панель). Роль в сессии вкладки обновляется. */
export async function signInPersona(session: DemoSessionStore, login: string) {
  const result = await api.post<LoginOut>('/demo/login-as', { login })
  if (result.ok) { tokenStore.write(result.data.accessToken); session.writeRole(result.data.user.role); revisionStore.bump() }
  return result
}
