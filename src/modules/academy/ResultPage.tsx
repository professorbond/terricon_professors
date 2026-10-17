import { useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router'
import { ArrowLeft } from 'lucide-react'
import { WorkspaceHeading } from '@/components/ui/WorkspaceHeading'
import { Button } from '@/components/ui/Button'
import { api } from '@/services/http/client'
import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { ExtState } from '../ext-core/ui'
import type { CourseDetail, SubmitOut } from './types'
import './i18n'

/** Тест курса и результат. Правильные ответы сервер не присылает — проверка только на бэкенде. */
export default function ResultPage() {
  const t = useT()
  const { courseId = '' } = useParams()
  const q = useApi<CourseDetail>(`/academy/courses/${encodeURIComponent(courseId)}`)
  const [answers, setAnswers] = useState<Record<string, number>>({})
  const [result, setResult] = useState<SubmitOut | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const c = q.data
  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!c) return
    if (c.questions.some((qq) => answers[qq.id] === undefined)) { setError(t('ac.answerAll')); return }
    setBusy(true)
    const r = await api.post<SubmitOut>(`/academy/courses/${encodeURIComponent(courseId)}/submit`, { answers: c.questions.map((qq) => answers[qq.id]) })
    setBusy(false)
    if (r.ok) { setResult(r.data); setError(null) } else setError(r.problem.message)
  }
  return <div className="business-page"><Link className="back-link" to={`/academy/${courseId}`}><ArrowLeft size={16} aria-hidden="true" />{c?.title ?? t('ac.toCourse')}</Link>
    <WorkspaceHeading index={t('ac.index')} title={t('ac.test')}>{c && t('ac.testHint', { n: c.questions.length, score: c.passingScore })}</WorkspaceHeading>
    <ExtState loading={q.loading} problem={q.problem} retry={q.refresh}>{c && (result ? <section className="decision-complete ext-sent" role="status" data-testid="test-result" data-tone={result.passed ? 'normal' : 'warm'}><div>
        <h2>{result.passed ? t('ac.passed', { score: result.score }) : t('ac.failed', { score: result.score, need: result.passingScore })}</h2>
        <p>{t('ac.correct', { n: result.correct, total: result.total })}</p>
        <div className="ext-actions"><Link className="button button--primary" to="/academy">{t('ac.back')}</Link>{!result.passed && <Button variant="secondary" onClick={() => { setResult(null); setAnswers({}) }}>{t('ac.retry')}</Button>}</div></div></section>
      : <form className="ext-section" onSubmit={submit} noValidate data-testid="test-form">
        {c.questions.map((qq) => <fieldset className="ext-question" key={qq.id}><legend>{qq.ord}. {qq.text}</legend>
          {qq.options.map((o, i) => <label key={i}><input type="radio" name={qq.id} checked={answers[qq.id] === i} onChange={() => { setAnswers((a) => ({ ...a, [qq.id]: i })); setError(null) }} />{o}</label>)}</fieldset>)}
        {error && <p className="field-error" role="alert">{error}</p>}
        <Button type="submit" disabled={busy} aria-busy={busy}>{busy ? t('common.sending') : t('ac.submit')}</Button>
      </form>)}</ExtState>
  </div>
}
