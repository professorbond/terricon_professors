import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { MIN_REJECT_COMMENT, useRejectReasonRequired } from './rejectRules'
import './i18n'

/** Выбор причины отказа для окна решения (CLAUDE.md §7.1). Без гарантий — ничего не рендерит. */
export function RejectReason({ type = 'vacation', value, onChange, disabled }: { type?: string; value: string; onChange: (code: string) => void; disabled?: boolean }) {
  const t = useT()
  const required = useRejectReasonRequired()
  const reasons = useApi<{ code: string; title: string }[]>(required ? `/ext/guarantees/reasons?type=${type}` : null)
  if (!required) return null
  return <label className="comment-field ext-reason"><span>{t('g.reason')} <small>{t('g.required')}</small></span>
    <select value={value} required disabled={disabled} onChange={(e) => onChange(e.target.value)}>
      <option value="">{t('g.reasonPick')}</option>
      {(reasons.data ?? []).map((r) => <option key={r.code} value={r.code}>{r.title}</option>)}
    </select>
    <small className="field-hint">{t('g.reasonHint', { n: MIN_REJECT_COMMENT })}</small>
  </label>
}
