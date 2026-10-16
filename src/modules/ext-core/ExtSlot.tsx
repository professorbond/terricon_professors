import { Suspense } from 'react'
import { slotParts, type SlotName } from './registry'
import { useSettings } from './settings'

/** Слот: рендерит блоки включённых ext-модулей. Без API (режим моков) — ничего. */
export function ExtSlot({ name, requestId }: { name: SlotName; requestId?: string }) {
  useSettings() // перерисовка при смене флагов
  const parts = slotParts(name)
  if (!parts.length) return null
  // Каждый блок со своей границей: загрузка блока не замораживает страницу напарника
  return <>{parts.map(({ C, key }) => <Suspense key={key} fallback={null}><C {...(requestId ? { requestId } : {})} /></Suspense>)}</>
}
