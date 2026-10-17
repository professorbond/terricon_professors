import { useEffect } from 'react'
import { Link, useParams } from 'react-router'
import { ArrowLeft, ArrowUpRight, Check } from 'lucide-react'
import { WorkspaceHeading } from '@/components/ui/WorkspaceHeading'
import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { ExtState, Pill } from '../ext-core/ui'
import { GradeTag } from './GradeTag'
import type { CourseDetail } from './types'
import './i18n'

export default function CoursePage() {
  const t = useT()
  const { courseId = '' } = useParams()
  const q = useApi<CourseDetail>(`/academy/courses/${encodeURIComponent(courseId)}`)
  const c = q.data
  useEffect(() => { if (c) document.title = `${c.title} · JanaМен` }, [c])
  const next = c?.lessons.find((l) => !l.completed)
  return <div className="business-page"><Link className="back-link" to="/academy"><ArrowLeft size={16} aria-hidden="true" />{t('ac.back')}</Link>
    <WorkspaceHeading index={t('ac.index')} title={c?.title ?? t('ac.title')}>{c?.description}</WorkspaceHeading>
    <ExtState loading={q.loading} problem={q.problem} retry={q.refresh}>{c && <>
      <div className="ext-row"><Pill tone={c.progress?.status === 'Completed' ? 'success' : 'neutral'}>{t(`ac.status.${c.progress?.status ?? 'Assigned'}`)}</Pill><GradeTag courseId={c.id} />
        {c.progress?.scorePercent !== null && c.progress?.scorePercent !== undefined && <span className="ext-muted">{t('ac.score', { n: c.progress.scorePercent })}</span>}</div>
      <section className="ext-section" aria-labelledby="ac-l"><span className="eyebrow">01</span><h2 id="ac-l">{t('ac.lessonsTitle')}</h2>
        <ol className="ext-list" data-testid="course-lessons">{c.lessons.map((l) => <li key={l.id}><div><strong>{l.ord}. {l.title}</strong>{l.completed && <span className="ext-muted"><Check size={14} aria-hidden="true" /> {t('ac.done')}</span>}</div>
          <Link className="text-link" to={`/academy/${c.id}/lessons/${l.id}`}>{l.completed ? t('ac.open') : l.id === next?.id ? t('ac.continue') : t('ac.open')} <ArrowUpRight size={15} aria-hidden="true" /></Link></li>)}</ol></section>
      <section className="ext-section" aria-labelledby="ac-t"><span className="eyebrow">02</span><h2 id="ac-t">{t('ac.test')}</h2><p className="ext-muted">{t('ac.testHint', { n: c.questions.length, score: c.passingScore })}</p>
        <Link className="button button--primary" to={`/academy/${c.id}/result`}>{t('ac.goTest')} <ArrowUpRight size={16} aria-hidden="true" /></Link></section>
    </>}</ExtState>
  </div>
}
