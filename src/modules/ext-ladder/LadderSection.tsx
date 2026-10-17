import { Link } from 'react-router'
import { ArrowUpRight } from 'lucide-react'
import { registerDictionary, useT } from '../ext-core/i18n'
import { useApi } from '../ext-core/useApi'
import { money, shortDate } from '../ext-core/format'
import { ExtState, Pill } from '../ext-core/ui'

registerDictionary(
  { 'l.eyebrow': 'МОЯ ЛЕСТНИЦА', 'l.title': 'Открытая лестница', 'l.lead': 'Сколько можно зарабатывать и что для этого сделать. Видны только ваш и следующий грейд.', 'l.now': 'Сейчас', 'l.next': 'Дальше', 'l.top': 'Это верхний грейд в вашей линии',
    'l.remaining': 'Осталось: {n} курс → +{raise} к нижней границе', 'l.ready': 'Все условия выполнены — HR рассмотрит переход при пересмотре', 'l.raise': '+{raise} к нижней границе', 'l.review': 'Следующий пересмотр зарплаты: {date}',
    'l.toCourse': 'Перейти к курсу', 'l.monthsOf': '{actual} из {required} мес' },
  { 'l.eyebrow': 'МЕНІҢ САТЫМ', 'l.title': 'Ашық саты', 'l.lead': 'Қанша табуға болады және ол үшін не істеу керек. Тек сіздің және келесі грейд көрінеді.', 'l.now': 'Қазір', 'l.next': 'Келесі', 'l.top': 'Бұл сіздің бағыттағы жоғарғы грейд',
    'l.remaining': 'Қалды: {n} курс → төменгі шекке +{raise}', 'l.ready': 'Барлық шарттар орындалды — HR қайта қарауда өтуді қарастырады', 'l.raise': 'төменгі шекке +{raise}', 'l.review': 'Жалақыны келесі қайта қарау: {date}',
    'l.toCourse': 'Курсқа өту', 'l.monthsOf': '{required} айдан {actual}' },
)

interface Grade { code: string; title: string; bandMin: number; bandMax: number; currency: string }
interface Criterion { kind: string; title: string; done: boolean; courseId?: string | null; required?: number | null; actual?: number | null }
interface Ladder { current: Grade | null; next: Grade | null; criteria: Criterion[]; remainingCourses: number; raiseToNextMin: number | null; nextReviewDate: string | null; ready: boolean }

const band = (g: Grade) => `${money(g.bandMin, g.currency)} — ${money(g.bandMax, g.currency)}`

/** Блок в профиле: «Сейчас: Сортировщик · 230–270 тыс ₸ → Дальше: Старший сортировщик · 275–320 тыс ₸». */
export default function LadderSection() {
  const t = useT()
  const q = useApi<Ladder>('/ext/ladder/me')
  const l = q.data
  const course = l?.criteria.find((c) => c.kind === 'course' && !c.done)
  return <section className="ext-section" aria-labelledby="l-title" data-testid="ladder">
    <span className="eyebrow">{t('l.eyebrow')}</span><h2 id="l-title">{t('l.title')}</h2><p className="ext-muted">{t('l.lead')}</p>
    <ExtState loading={q.loading} problem={q.problem} retry={q.refresh}>{l?.current && <>
      <div className="ext-ladder">
        <div><span className="eyebrow">{t('l.now')}</span><p><strong>{l.current.title}</strong> · {l.current.code}</p><p className="ext-muted">{band(l.current)}</p></div>
        <span className="ext-ladder-arrow" aria-hidden="true">→</span>
        {l.next ? <div><span className="eyebrow">{t('l.next')}</span><p><strong>{l.next.title}</strong> · {l.next.code}</p><p className="ext-muted">{band(l.next)}</p></div> : <p className="ext-muted">{t('l.top')}</p>}
      </div>
      {l.next && <>
        <ul className="ext-criteria">{l.criteria.map((c) => <li key={c.kind + (c.courseId ?? '')} data-done={c.done}>{c.title}{c.required != null && c.actual != null && <span className="ext-muted"> · {t('l.monthsOf', { actual: c.actual, required: c.required })}</span>}</li>)}</ul>
        <p className="ext-figure" style={{ fontSize: '1.6rem', margin: '1rem 0 1.25rem' }} data-testid="ladder-remaining">
          {l.ready ? t('l.ready') : l.remainingCourses ? t('l.remaining', { n: l.remainingCourses, raise: money(l.raiseToNextMin ?? 0, l.next.currency) }) : t('l.raise', { raise: money(l.raiseToNextMin ?? 0, l.next.currency) })}</p>
        {course && <Link className="button button--primary" to={`/academy/${course.courseId}`}>{t('l.toCourse')} <ArrowUpRight size={16} aria-hidden="true" /></Link>}
      </>}
      {l.nextReviewDate && <p style={{ marginTop: '1rem' }}><Pill tone="info">{t('l.review', { date: shortDate(l.nextReviewDate, true) })}</Pill></p>}
    </>}</ExtState>
  </section>
}
