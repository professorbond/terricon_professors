import { apiEnabled } from '@/services/http/client'
import { featureEnabled, useSettings } from '../ext-core/settings'

export const MIN_REJECT_COMMENT = 10

/** Нужна ли причина из справочника при отказе (гарантии включены и работаем с API). */
export function useRejectReasonRequired(): boolean {
  useSettings()
  return apiEnabled && featureEnabled('guarantees')
}
