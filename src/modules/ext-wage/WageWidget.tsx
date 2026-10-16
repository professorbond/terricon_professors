import { Link } from 'react-router'
import { ArrowUpRight } from 'lucide-react'
import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { money } from '../ext-core/format'
import { ExtState } from '../ext-core/ui'
import type { WageSummary } from './types'
import './i18n'

/** Блок на главной: «Доступно сейчас 84 000 ₸» → «Получить» (1-е нажатие из трёх). */
export default function WageWidget() {
  const t = useT()
  const q = useApi<WageSummary>('/ext/wage/summary')
  return <section className="ext-section" aria-labelledby="w-widget" data-testid="wage-widget">
    <span className="eyebrow">{t('w.widget.eyebrow')}</span><h2 id="w-widget">{t('w.title')}</h2>
    <ExtState loading={q.loading} problem={q.problem} retry={q.refresh}>{q.data && <div className="ext-row ext-row--between">
      <div><span className="eyebrow">{t('w.available')}</span><p className="ext-figure" data-testid="wage-available">{money(q.data.available, q.data.currency)}</p>
        <p className="ext-muted">{t('w.worked', { n: q.data.shiftsWorked, plan: q.data.shiftsPlanned, earned: money(q.data.earned, q.data.currency) })}</p></div>
      <Link className="button button--primary" to="/wage">{t('w.get')} <ArrowUpRight size={18} aria-hidden="true" /></Link>
    </div>}</ExtState>
  </section>
}
