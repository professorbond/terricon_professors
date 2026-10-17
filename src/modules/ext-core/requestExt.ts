import { useEffect, useState, useSyncExternalStore } from 'react'
import { api, revisionStore } from '@/services/http/client'

/** Расширения карточки заявки (extensions.guarantee и др.) с кэшем на текущую ревизию —
 * список из N строк не делает лишних повторных запросов при перерисовке. */
export interface GuaranteeExt { deadlineAt: string; resolution: 'none' | 'auto_approved' | 'escalated' | 'overdue'; overdue: boolean; decidedLate: boolean }
interface RequestExt { status: string; extensions: { guarantee?: GuaranteeExt } }

const cache = new Map<string, Promise<RequestExt | null>>()
let cachedRevision = -1

function load(id: string): Promise<RequestExt | null> {
  const rev = revisionStore.getRevision()
  if (rev !== cachedRevision) { cache.clear(); cachedRevision = rev }
  let p = cache.get(id)
  if (!p) { p = api.get<RequestExt>(`/requests/${encodeURIComponent(id)}`).then((r) => (r.ok ? r.data : null)); cache.set(id, p) }
  return p
}

export function useRequestExt(id: string | undefined) {
  const revision = useSyncExternalStore(revisionStore.subscribe, revisionStore.getRevision)
  const [data, setData] = useState<{ id: string; value: RequestExt | null } | null>(null)
  useEffect(() => {
    if (!id) return
    let active = true
    void load(id).then((value) => { if (active) setData({ id, value }) })
    return () => { active = false }
  }, [id, revision])
  return data && data.id === id ? data.value : null
}
