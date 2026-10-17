import { lazy } from 'react'
import type { ExtModule } from '../ext-core/registry'

export const ladderModule: ExtModule = {
  id: 'ext-ladder',
  feature: 'ladder',
  slots: { 'profile.sections': [lazy(() => import('./LadderSection'))] },
}
