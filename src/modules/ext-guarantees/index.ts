import { lazy } from 'react'
import type { ExtModule } from '../ext-core/registry'

export const guaranteesModule: ExtModule = {
  id: 'ext-guarantees',
  feature: 'guarantees',
  slots: {
    'home.widgets': [lazy(() => import('./GuaranteesWidget'))],
    'request.list.badge': [lazy(() => import('./GuaranteeBadge'))],
    'request.card.badges': [lazy(() => import('./GuaranteeBadge'))],
  },
}
