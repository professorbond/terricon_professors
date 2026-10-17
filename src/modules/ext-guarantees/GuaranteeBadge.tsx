import { useRequestExt } from '../ext-core/requestExt'
import { useT } from '../ext-core/i18n'
import { dateTime } from '../ext-core/format'
import { Pill } from '../ext-core/ui'
import './i18n'

/** Бейдж гарантии в списке и карточке заявки: «Ответ до …» / «Одобрено по сроку» / «Передано HR». */
export default function GuaranteeBadge({ requestId }: { requestId?: string }) {
  const t = useT()
  const ext = useRequestExt(requestId)
  const g = ext?.extensions.guarantee
  if (!g) return null
  let badge: React.ReactNode = null
  if (g.resolution === 'auto_approved') badge = <Pill tone="success">{t('g.badge.auto')}</Pill>
  else if (g.resolution === 'escalated' || ext.status === 'Escalated') badge = <Pill tone="info">{t('g.badge.escalated')}</Pill>
  else if (g.overdue || g.resolution === 'overdue') badge = <Pill tone="warning">{t('g.badge.overdue')}</Pill>
  else if (g.decidedLate) badge = <Pill tone="warning">{t('g.badge.late')}</Pill>
  else if (ext.status === 'Submitted') badge = <Pill>{t('g.badge.until', { date: dateTime(g.deadlineAt) })}</Pill>
  return badge ? <span className="ext-badges" data-testid="guarantee-badge">{badge}</span> : null
}
