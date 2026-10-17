/** Ext-модули фронтенда. Одна строка на модуль — при мерже только добавлять. */
import { registerModules } from './ext-core/registry'
import { guaranteesModule } from './ext-guarantees'
import { wageModule } from './ext-wage'
import { hrConsoleModule } from './ext-hr'
import { academyModule } from './academy'
import { ladderModule } from './ext-ladder'
import { policiesModule } from './ext-policies'
import './ext-policies/i18n'
import './ext-wage/i18n'
import './ext-hr/i18n'
import './academy/i18n'

registerModules([
  wageModule,
  guaranteesModule,
  hrConsoleModule,
  academyModule,
  ladderModule,
  policiesModule,
])

export { extElement, extNavigation, extPlannedScreens } from './ext-core/registry'
export { ExtSlot } from './ext-core/ExtSlot'
export { RejectReason } from './ext-guarantees/RejectReason'
export { useRejectReasonRequired, MIN_REJECT_COMMENT } from './ext-guarantees/rejectRules'
