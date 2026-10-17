import { useRef, useState, type FormEvent } from 'react'
import { Check, X } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { motionTokens } from '@/styles/motion'
import { SegmentedControl } from '@/components/motion/SegmentedControl'
import { Button } from '@/components/ui/Button'
import { useServices } from '@/services/context'
import type { LeaveRequest } from '../model'
import { MIN_REJECT_COMMENT, RejectReason, useRejectReasonRequired } from '@/modules'

export function DecisionPanel({ request }: { request: LeaveRequest }) {
  const services = useServices()
  const [decision, setDecision] = useState<'Approved' | 'Rejected'>('Approved')
  const [comment, setComment] = useState('')
  const [reasonCode, setReasonCode] = useState('')
  const reasonRequired = useRejectReasonRequired()
  const rejectIncomplete = decision === 'Rejected' && reasonRequired && (!reasonCode || comment.trim().length < MIN_REJECT_COMMENT)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const sending = useRef(false)
  const reason = useRef<HTMLTextAreaElement>(null)
  const reduce = useReducedMotion()
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (sending.current || request.status !== 'Submitted') return
    if (decision === 'Rejected' && !comment.trim()) { setError('Укажите причину отклонения.'); reason.current?.focus(); return }
    sending.current = true
    setBusy(true)
    setError(null)
    const result = await services.leaveRequests.decide(request.id, decision === 'Rejected' && reasonCode ? { decision, comment, reasonCode, expectedVersion: request.version } : { decision, comment, expectedVersion: request.version })
    if (!result.ok) setError(result.problem.message)
    sending.current = false
    setBusy(false)
  }
  if (request.status !== 'Submitted') return <motion.div className="decision-complete" data-tone={request.status === 'Rejected' ? 'warm' : 'normal'} role="status" initial={reduce ? false : { opacity: 0.5, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={reduce ? { duration: 0 } : motionTokens.transition}>{request.status === 'Rejected' ? <X size={19} aria-hidden="true" /> : <Check size={19} aria-hidden="true" />}<p>Решение сохранено. Сотруднику создано уведомление.<small>Повторное решение по этой заявке недоступно.</small></p></motion.div>
  return <section className="decision-panel"><div><span className="eyebrow">ВАШ ХОД / 02</span><h2>Решение по заявке</h2><p>Результат сразу появится у сотрудника.</p></div><form onSubmit={submit} noValidate><SegmentedControl label="Решение руководителя" value={decision} disabled={busy} onChange={(value) => { setDecision(value); setError(null) }} options={[{ value: 'Approved', label: 'Согласовать', icon: <Check size={18} aria-hidden="true" /> }, { value: 'Rejected', label: 'Отклонить', icon: <X size={18} aria-hidden="true" />, tone: 'warm' }]} /><label className="comment-field"><span>{decision === 'Rejected' ? 'Причина отклонения' : 'Комментарий к решению'} <small>{decision === 'Rejected' ? 'обязательно' : 'необязательно'}</small></span><textarea ref={reason} value={comment} required={decision === 'Rejected'} maxLength={1000} rows={3} disabled={busy} aria-invalid={!!error} aria-describedby={error ? 'decision-error' : undefined} onChange={(event) => { setComment(event.target.value); setError(null) }} /></label>{decision === 'Rejected' && <RejectReason value={reasonCode} onChange={(code) => { setReasonCode(code); setError(null) }} disabled={busy} />}{error && <p id="decision-error" className="field-error" role="alert">{error}</p>}<Button type="submit" disabled={busy || rejectIncomplete} aria-busy={busy}>{busy ? 'Сохраняем…' : decision === 'Approved' ? 'Подтвердить согласование' : 'Подтвердить отклонение'}</Button></form></section>
}
