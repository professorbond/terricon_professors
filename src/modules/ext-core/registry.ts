import { createElement, Suspense, type ComponentType, type LazyExoticComponent, type ReactElement } from 'react'
import type { LucideIcon } from 'lucide-react'
import type { Role } from '@/features/identity/model'
import { apiEnabled } from '@/services/http/client'
import { featureEnabled } from './settings'
import { translate } from './i18n'

/** Места во фронтенде напарника, куда ext-модули вставляют свои блоки (CLAUDE.md §4.2). */
export type SlotName =
  | 'home.widgets'          // главная (DashboardPage)
  | 'profile.sections'      // профиль (ProfilePage)
  | 'request.list.badge'    // строка в «Мои заявки» / очереди (RequestList), props: { requestId }
  | 'request.card.badges'   // карточка заявки (RequestDetailPage), props: { requestId }

export interface ExtScreen {
  /** id экрана: новый или заглушка напарника (academy, ai-jana, hr …) */
  id: string
  path?: string // только для новых экранов
  titleKey: string
  roles: readonly Role[]
  component: LazyExoticComponent<ComponentType>
  feature?: string
}

export interface ExtNavItem { path: string; labelKey: string; icon: LucideIcon; roles: readonly Role[]; feature?: string; end?: boolean }

export interface ExtModule {
  id: string
  feature?: string
  screens?: ExtScreen[]
  nav?: ExtNavItem[]
  slots?: Partial<Record<SlotName, ComponentType<{ requestId?: string }>[]>>
}

let modules: ExtModule[] = []
export function registerModules(list: ExtModule[]) { modules = apiEnabled ? list : [] }

const enabled = (m: ExtModule) => featureEnabled(m.feature)

/** Новые маршруты для каталога экранов напарника (src/app/routes.ts). */
export function extPlannedScreens(): { id: string; path: string; title: string; roles: readonly Role[] }[] {
  return modules.flatMap((m) => (m.screens ?? []).filter((s) => s.path).map((s) => ({ id: s.id, path: s.path!, title: translate(s.titleKey), roles: s.roles })))
}

/** Элемент для экрана по id (новый или заглушка напарника). null — экрана нет, работает его логика. */
export function extElement(id: string): ReactElement | null {
  for (const m of modules) {
    const screen = m.screens?.find((s) => s.id === id)
    if (screen && enabled(m) && featureEnabled(screen.feature)) {
      const Comp = screen.component
      const fallback = createElement('p', { className: 'query-loading', role: 'status' }, translate('common.loading'))
      return createElement(Suspense, { fallback }, createElement(Comp))
    }
  }
  return null
}

/** Пункты меню ext-фич для роли — отдельной группой «Сервисы JanaМен». */
export function extNavigation(role: Role) {
  const items = modules.filter(enabled).flatMap((m) => m.nav ?? []).filter((i) => i.roles.includes(role) && featureEnabled(i.feature))
  return items.length ? [{ label: translate('nav.ext.group'), items: items.map((i, n) => ({ path: i.path, label: translate(i.labelKey), icon: i.icon, index: String(10 + n).padStart(2, '0'), ...(i.end ? { end: true } : {}) })) }] : []
}

/** Блоки слота для включённых модулей (рендер — в ExtSlot.tsx). */
export function slotParts(name: SlotName) {
  return modules.filter(enabled).flatMap((m) => (m.slots?.[name] ?? []).map((C, i) => ({ C, key: `${m.id}-${i}` })))
}
