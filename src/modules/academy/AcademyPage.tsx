import { useEffect } from 'react'
import { Link } from 'react-router'
import { ArrowUpRight } from 'lucide-react'
import { WorkspaceHeading } from '@/components/ui/WorkspaceHeading'
import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { shortDate } from '../ext-core/format'
import { ExtState, LangSwitch, Pill } from '../ext-core/ui'
import { GradeTag } from './GradeTag'
import type { Assigned, CourseSummary } from './types'
import './i18n'

const tone = { Assigned: 'neutral', InProgress: 'warning', Completed: 'success' } as const

export default function AcademyPage() {
  const t = useT()
  const my = useApi<{ items: Assigned[] }>('/academy/my')
  const catalog = useApi<{ items: CourseSummary[] }>('/academy/courses')
  useEffect(() => { document.title = `${t('ac.title')} · JanaМен` }, [t])
  const mine = new Set(my.data?.items.map((c) => c.id))
  return <div className="business-page">
    <WorkspaceHeading index={t('ac.index')} title={t('ac.title')}>{t('ac.lead')}</WorkspaceHeading>
    <div className="ext-row ext-row--between"><span /><LangSwitch /></div>
    <section className="ext-section" aria-labelledby="ac-mine"><span className="eyebrow">01</span><h2 id="ac-mine">{t('ac.assigned')}</h2>
      <ExtState loading={my.loading} problem={my.problem} retry={my.refresh} empty={!!my.data && !my.data.items.length} emptyTitle={t('ac.noAssigned')} emptyText={t('ac.noAssignedText')}>
        <ul className="ext-list" data-testid="academy-my">{my.data?.items.map((c) => <li key={c.id}>
          <div><strong>{c.title}</strong><span className="ext-muted">{c.description}</span>
            <div className="ext-row" style={{ marginTop: '.4rem' }}><Pill tone={tone[c.progress.status]}>{t(`ac.status.${c.progress.status}`)}</Pill>
              {c.progress.scorePercent !== null && <span className="ext-muted">{t('ac.score', { n: c.progress.scorePercent })}</span>}
              {c.dueDate && c.progress.status !== 'Completed' && <span className="ext-muted">{t('ac.due', { date: shortDate(c.dueDate) })}</span>}<GradeTag courseId={c.id} /></div>
            <div className="ext-progress" aria-hidden="true"><span style={{ width: `${c.progress.lessonsPercent}%` }} /></div>
            <span className="ext-muted">{t('ac.lessons', { done: c.progress.completedLessonIds.length, total: c.progress.totalLessons })} · {t('ac.min', { n: c.durationMinutes })}</span></div>
          <Link className={`button ${c.progress.status === 'Completed' ? 'button--secondary' : 'button--primary'}`} to={`/academy/${c.id}`}>{c.progress.status === 'Assigned' ? t('ac.start') : c.progress.status === 'Completed' ? t('ac.open') : t('ac.continue')} <ArrowUpRight size={16} aria-hidden="true" /></Link>
        </li>)}</ul>
      </ExtState></section>
    <section className="ext-section" aria-labelledby="ac-cat"><span className="eyebrow">02</span><h2 id="ac-cat">{t('ac.catalog')}</h2>
      <ExtState loading={catalog.loading} problem={catalog.problem} retry={catalog.refresh}>
        <ul className="ext-list">{catalog.data?.items.filter((c) => !mine.has(c.id)).map((c) => <li key={c.id}><div><strong>{c.title}</strong><span className="ext-muted">{c.description} · {t('ac.min', { n: c.durationMinutes })}</span><GradeTag courseId={c.id} /></div>
          <Link className="text-link" to={`/academy/${c.id}`}>{t('ac.open')} <ArrowUpRight size={16} aria-hidden="true" /></Link></li>)}</ul>
      </ExtState></section>
  </div>
}
