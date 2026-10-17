import { useEffect, useState, type FormEvent } from 'react'
import { WorkspaceHeading } from '@/components/ui/WorkspaceHeading'
import { Button } from '@/components/ui/Button'
import { api } from '@/services/http/client'
import { useDemoSession } from '@/features/identity/demo-context'
import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { shortDate, todayAlmaty } from '../ext-core/format'
import { ExtState, LangSwitch, Pill } from '../ext-core/ui'
import type { CourseSummary, Progress } from './types'
import './i18n'

interface Row { employeeId: string; employeeName: string; unitId: string; courseId: string; courseTitle: string; dueDate: string | null; progress: Progress }
interface Person { id: string; displayName: string; position: string }
const tone = { Assigned: 'neutral', InProgress: 'warning', Completed: 'success' } as const

/** HR (/hr/learning) и руководитель: прогресс обучения и назначение курса (CLAUDE.md §5.4, §5.5). */
export default function LearningAdminPage() {
  const t = useT()
  const { user } = useDemoSession()
  const progress = useApi<{ items: Row[] }>('/academy/progress')
  const people = useApi<{ items: Person[] }>('/team')
  const courses = useApi<{ items: CourseSummary[] }>('/academy/courses')
  const [form, setForm] = useState({ employeeId: '', courseId: '', dueDate: '' })
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)
  useEffect(() => { document.title = `${t('ac.hr.title')} · JanaМен` }, [t])
  async function assign(e: FormEvent) {
    e.preventDefault()
    const r = await api.post('/academy/assignments', { employeeId: form.employeeId, courseId: form.courseId, ...(form.dueDate ? { dueDate: form.dueDate } : {}) })
    setMessage(r.ok ? { ok: true, text: t('ac.hr.assigned') } : { ok: false, text: r.problem.message })
  }
  return <div className="business-page">
    <WorkspaceHeading index={user?.role === 'HRAdmin' ? 'HR / ОБУЧЕНИЕ' : '02 / КОМАНДА'} title={t('ac.hr.title')}>{t('ac.hr.lead')}</WorkspaceHeading>
    <div className="ext-row ext-row--between"><span /><LangSwitch /></div>
    <section className="ext-section"><span className="eyebrow">01</span><h2>{t('ac.hr.progress')}</h2>
      <ExtState loading={progress.loading} problem={progress.problem} retry={progress.refresh} empty={!!progress.data && !progress.data.items.length}>
        <div className="ext-table-scroll" role="region" tabIndex={0} aria-label={t('ac.hr.progress')}><table className="ext-table" data-testid="learning-progress"><thead><tr><th>{t('ac.hr.employee')}</th><th>{t('ac.hr.course')}</th><th>{t('ac.hr.progress')}</th><th>{t('ac.hr.due')}</th></tr></thead>
          <tbody>{progress.data?.items.map((r) => <tr key={r.employeeId + r.courseId}><td>{r.employeeName}</td><td>{r.courseTitle}</td>
            <td><Pill tone={tone[r.progress.status]}>{t(`ac.status.${r.progress.status}`)}</Pill> <span className="ext-muted">{r.progress.lessonsPercent}%{r.progress.scorePercent !== null ? ` · ${r.progress.scorePercent}%` : ''}</span></td>
            <td>{r.dueDate ? shortDate(r.dueDate, true) : '—'}</td></tr>)}</tbody></table></div>
      </ExtState></section>
    <section className="ext-section"><span className="eyebrow">02</span><h2>{t('ac.hr.assign')}</h2>
      <form className="ext-form" onSubmit={assign}>
        <label><span>{t('ac.hr.employee')}</span><select required value={form.employeeId} onChange={(e) => setForm({ ...form, employeeId: e.target.value })}><option value="" />{people.data?.items.map((p) => <option key={p.id} value={p.id}>{p.displayName} — {p.position}</option>)}</select></label>
        <label><span>{t('ac.hr.course')}</span><select required value={form.courseId} onChange={(e) => setForm({ ...form, courseId: e.target.value })}><option value="" />{courses.data?.items.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}</select></label>
        <label><span>{t('ac.hr.due')}</span><input type="date" min={todayAlmaty()} value={form.dueDate} onChange={(e) => setForm({ ...form, dueDate: e.target.value })} /></label>
        {message && <p className={message.ok ? 'ext-muted' : 'field-error'} role={message.ok ? 'status' : 'alert'}>{message.text}</p>}
        <div className="ext-actions"><Button type="submit" disabled={!form.employeeId || !form.courseId}>{t('ac.hr.assign')}</Button></div>
      </form></section>
  </div>
}
