import { BookOpen, CircleHelp, ClipboardList, GraduationCap, House, Layers3, Network, NotebookText, Sparkles, UsersRound } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { Role } from '@/features/identity/model'
import { extNavigation } from '@/modules'

export interface NavigationItem { path: string; label: string; icon: LucideIcon; index: string; end?: boolean }
export interface NavigationGroup { label: string; items: NavigationItem[] }

const personal: NavigationGroup = {
  label: 'Личное пространство',
  items: [
    { path: '/dashboard', label: 'Мой день', icon: House, index: '01' },
    { path: '/requests', label: 'Мои заявки', icon: ClipboardList, index: '02' },
    { path: '/academy', label: 'Jana Academy', icon: GraduationCap, index: '03' },
    { path: '/ai-jana', label: 'AI Jana', icon: Sparkles, index: '04' },
  ],
}

export function getNavigation(role: Role): NavigationGroup[] {
  return [...baseNavigation(role), ...extNavigation(role)]
}

function baseNavigation(role: Role): NavigationGroup[] {
  if (role === 'Manager') return [personal, { label: 'Команда', items: [
    { path: '/manager/approvals', label: 'Согласования', icon: Layers3, index: '05' },
    { path: '/manager/team', label: 'Моя команда', icon: UsersRound, index: '06' },
  ] }]
  if (role === 'HRAdmin') return [personal, { label: 'Рабочее пространство HR', items: [
    { path: '/hr', label: 'Обзор HR', icon: Network, index: '05', end: true },
    { path: '/hr/requests', label: 'Реестр заявок', icon: Layers3, index: '06' },
    { path: '/hr/employees', label: 'Сотрудники', icon: UsersRound, index: '07' },
    { path: '/hr/learning', label: 'Обучение', icon: BookOpen, index: '08' },
    { path: '/hr/knowledge', label: 'База знаний', icon: NotebookText, index: '09' },
  ] }]
  return [personal]
}

export const supportNavigation = { path: '/ai-jana', label: 'Помощь рядом', icon: CircleHelp }
