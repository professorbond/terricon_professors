import { lazy } from 'react'
import { Gauge } from 'lucide-react'
import type { ExtModule } from '../ext-core/registry'

/** HR-пульт занимает стартовую страницу HR (/hr — заглушка напарника «Обзор HR»). */
export const hrConsoleModule: ExtModule = {
  id: 'ext-hr',
  screens: [
    { id: 'hr', titleKey: 'hr.title', roles: ['HRAdmin'], component: lazy(() => import('./HrConsolePage')) },
    { id: 'ext-xray-me', path: '/manager/xray', titleKey: 'xr.me.title', roles: ['Manager'], component: lazy(() => import('./MyXrayPage')), feature: 'xray' },
  ],
  nav: [{ path: '/manager/xray', labelKey: 'xr.me.nav', icon: Gauge, roles: ['Manager'], feature: 'xray' }],
}

