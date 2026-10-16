/** Ext-модули фронтенда. Одна строка на модуль — при мерже только добавлять. */
import { registerModules } from './ext-core/registry'
import { guaranteesModule } from './ext-guarantees'
import { wageModule } from './ext-wage'
import './ext-wage/i18n'

registerModules([
  wageModule,
  guaranteesModule,
])

export { extElement, extNavigation, extPlannedScreens } from './ext-core/registry'
export { ExtSlot } from './ext-core/ExtSlot'
