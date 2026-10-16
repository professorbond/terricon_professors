/** Ext-модули фронтенда. Одна строка на модуль — при мерже только добавлять. */
import { registerModules } from './ext-core/registry'

registerModules([])

export { extElement, extNavigation, extPlannedScreens } from './ext-core/registry'
export { ExtSlot } from './ext-core/ExtSlot'
