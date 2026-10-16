import { slotParts, type SlotName } from './registry'
import { useSettings } from './settings'

/** Слот: рендерит блоки включённых ext-модулей. Без API (режим моков) — ничего. */
export function ExtSlot({ name, requestId }: { name: SlotName; requestId?: string }) {
  useSettings() // перерисовка при смене флагов
  const parts = slotParts(name)
  if (!parts.length) return null
  return <>{parts.map(({ C, key }) => <C key={key} {...(requestId ? { requestId } : {})} />)}</>
}
