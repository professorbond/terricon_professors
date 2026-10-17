import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ArrowLeft, Check } from 'lucide-react'
import { WorkspaceHeading } from '@/components/ui/WorkspaceHeading'
import { Button } from '@/components/ui/Button'
import { api } from '@/services/http/client'
import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { Markdown } from '../ext-core/Markdown'
import { ExtState } from '../ext-core/ui'
import type { CourseDetail } from './types'
import './i18n'

export default function LessonPage() {
  const t = useT()
  const navigate = useNavigate()
  const { courseId = '', lessonId = '' } = useParams()
  const q = useApi<CourseDetail>(`/academy/courses/${encodeURIComponent(courseId)}`)
  const [busy, setBusy] = useState(false)
  const lessons = q.data?.lessons ?? []
  const index = lessons.findIndex((l) => l.id === lessonId)
  const lesson = lessons[index]
  const next = lessons[index + 1]
  async function done() {
    setBusy(true)
    await api.post(`/academy/lessons/${encodeURIComponent(lessonId)}/complete`)
    setBusy(false)
    navigate(next ? `/academy/${courseId}/lessons/${next.id}` : `/academy/${courseId}/result`)
  }
  return <div className="business-page"><Link className="back-link" to={`/academy/${courseId}`}><ArrowLeft size={16} aria-hidden="true" />{q.data?.title ?? t('ac.toCourse')}</Link>
    <WorkspaceHeading index={`${t('ac.lessonsTitle').toUpperCase()} / ${String(index + 1).padStart(2, '0')}`} title={lesson?.title ?? t('ac.lessonsTitle')} />
    <ExtState loading={q.loading} problem={q.problem} retry={q.refresh}>{lesson && <>
      <article className="ext-section" data-testid="lesson-content"><Markdown text={lesson.contentMd} /></article>
      <div className="ext-actions"><Button onClick={() => void done()} disabled={busy} aria-busy={busy}><Check size={18} aria-hidden="true" />{next ? `${t('ac.markDone')} · ${t('ac.next')}` : `${t('ac.markDone')} · ${t('ac.goTest')}`}</Button></div>
    </>}</ExtState>
  </div>
}
