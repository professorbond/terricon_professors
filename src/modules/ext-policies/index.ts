import { lazy } from 'react'
import { SlidersHorizontal } from 'lucide-react'
import type { ExtModule } from '../ext-core/registry'

export const policiesModule: ExtModule = {
  id: 'ext-policies',
  feature: 'guarantees',
  screens: [{ id: 'ext-policies', path: '/hr/policies', titleKey: 'p.title', roles: ['HRAdmin'], component: lazy(() => import('./PoliciesPage')) }],
  nav: [{ path: '/hr/policies', labelKey: 'p.title', icon: SlidersHorizontal, roles: ['HRAdmin'] }],
}
