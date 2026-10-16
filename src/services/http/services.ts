import type { ApplicationServices, Page, ServiceResult } from '../contracts'
import type { DemoSessionStore } from '../demo-session'
import type { EmployeeProfile, Role, User } from '@/features/identity/model'
import type { LeaveRequest } from '@/features/leave/model'
import type { EmployeeNotification } from '@/features/notifications/model'
import { api, revisionStore, tokenStore } from './client'

interface LoginOut { accessToken: string; user: User }

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
      listMine: (options) => api.get<Page<LeaveRequest>>('/leave/my', options),
      listTeam: (options) => api.get<Page<LeaveRequest>>('/leave/team', options),
      listPendingApprovals: (options) => api.get<Page<LeaveRequest>>('/leave/pending', options),
      getById: (id, options) => api.get<LeaveRequest>(`/leave/${encodeURIComponent(id)}`, options),
      submit: (input, options) => api.post<LeaveRequest>('/leave', input, options),
      decide: (id, input, options) => api.post<LeaveRequest>(`/leave/${encodeURIComponent(id)}/decision`, input, options),
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
