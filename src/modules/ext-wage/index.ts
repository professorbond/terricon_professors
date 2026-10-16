import { lazy } from 'react'
import { Wallet } from 'lucide-react'
import type { ExtModule } from '../ext-core/registry'

const ALL = ['Employee', 'Manager', 'HRAdmin'] as const

export const wageModule: ExtModule = {
  id: 'ext-wage',
  feature: 'wage_access',
  screens: [{ id: 'ext-wage', path: '/wage', titleKey: 'w.title', roles: ALL, component: lazy(() => import('./WagePage')) }],
  nav: [{ path: '/wage', labelKey: 'w.nav', icon: Wallet, roles: ALL }],
  slots: { 'home.widgets': [lazy(() => import('./WageWidget'))] },
}
