import { Link } from 'react-router'
import { ArrowUpRight } from 'lucide-react'
import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { dateTime, money, shortDate, todayAlmaty } from '../ext-core/format'
import { ExtState, Pill } from '../ext-core/ui'
import { featureEnabled } from '../ext-core/settings'
import './i18n'

interface Summary { openRequests: { requestId: string; number: string; typeTitle: string; deadlineAt: string }[]; rejectionsWithoutReason: number; decidedOnTime: number; decidedTotal: number; nextSalaryReview: string | null }
interface Wage { available: number; currency: string }
interface Shift { id: string; date: string; startTime: string; endTime: string }

/** Блок «Мои гарантии» на главной (CLAUDE.md §7.1). */
export default function GuaranteesWidget() {
  const t = useT()
  const s = useApi<Summary>('/ext/guarantees/summary/me')
  const wage = useApi<Wage>(featureEnabled('wage_access') ? '/ext/wage/summary' : null)
  const shifts = useApi<{ items: Shift[] }>(featureEnabled('shifts') ? '/ext/shifts/my' : null)
  const next = shifts.data?.items[0]
  const now = new Date().toISOString()
  return <section className="ext-section" aria-labelledby="g-title" data-testid="guarantees-widget">
    <span className="eyebrow">{t('g.eyebrow')}</span><h2 id="g-title">{t('g.title')}</h2><p className="ext-muted">{t('g.lead')}</p>
    <ExtState loading={s.loading} problem={s.problem} retry={s.refresh}>{s.data && <div className="ext-grid">
      <div>{s.data.openRequests.length ? s.data.openRequests.map((r) => <p key={r.requestId}>
        <span className="eyebrow">{t('g.answerBy', { number: r.number })}</span>
        <Link className="text-link" to={`/requests/${r.requestId}`}><strong>{dateTime(r.deadlineAt)}</strong> <ArrowUpRight size={15} aria-hidden="true" /></Link>
        {r.deadlineAt < now && <> <Pill tone="warning">{t('g.overdue')}</Pill></>}
      </p>) : <><span className="eyebrow">{t('g.noOpen')}</span><p className="ext-muted">{t('g.noOpenHint')}</p></>}</div>
      <div><span className="eyebrow">{t('g.noReason')}</span><p className="ext-figure ext-figure--ink">{s.data.rejectionsWithoutReason}</p></div>
      <div><span className="eyebrow">{t('g.onTime')}</span><p className="ext-figure ext-figure--ink">{s.data.decidedTotal ? t('g.onTimeOf', { n: s.data.decidedOnTime, total: s.data.decidedTotal }) : '—'}</p></div>
      <div><span className="eyebrow">{t('g.review')}</span><p><strong>{s.data.nextSalaryReview ? shortDate(s.data.nextSalaryReview, true) : '—'}</strong>{s.data.nextSalaryReview && s.data.nextSalaryReview < todayAlmaty() && <> <Pill tone="warning">{t('g.reviewOverdue')}</Pill></>}</p></div>
      {wage.data && <div><span className="eyebrow">{t('g.wage')}</span><p className="ext-figure">{money(wage.data.available, wage.data.currency)}</p><Link className="text-link" to="/wage">{t('g.wageLink')} <ArrowUpRight size={15} aria-hidden="true" /></Link></div>}
      {featureEnabled('shifts') && <div><span className="eyebrow">{t('g.shift')}</span><p><strong>{next ? `${shortDate(next.date)}, ${next.startTime}–${next.endTime}` : t('g.noShift')}</strong></p></div>}
    </div>}</ExtState>
  </section>
}
