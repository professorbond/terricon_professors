import { ArrowDownRight, Check } from 'lucide-react'
import { motion, useReducedMotion } from 'motion/react'
import { motionTokens } from '@/styles/motion'
import { formatDate } from '../dates'
import type { LeaveRequest } from '../model'

/** Rendered only from a successfully saved request. Motion never performs a write. */
export function SubmissionConfirmation({ request }: { request: LeaveRequest }) {
  const reduce = useReducedMotion()
  return <motion.section className="creation-confirmation" role="status"
    initial={reduce ? false : { opacity: 0.5, y: 8 }} animate={{ opacity: 1, y: 0 }}
    transition={reduce ? { duration: 0 } : motionTokens.transition}>
    <span className="confirmation-mark"><Check size={24} aria-hidden="true" /></span>
    <div><span className="eyebrow">ЗАЯВКА СОЗДАНА</span><h2>Ваши планы — в движении</h2><p><strong>{request.number}</strong> · {formatDate(request.startDate)} — {formatDate(request.endDate)}</p><p>Следующий ответственный: {request.managerName}</p></div>
    <a className="text-link" href="#flow-map">Посмотреть маршрут <ArrowDownRight size={18} aria-hidden="true" /></a>
  </motion.section>
}
