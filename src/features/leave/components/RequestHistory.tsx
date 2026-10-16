import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { AnimatedValue } from '@/components/motion/AnimatedValue'
import { motionTokens } from '@/styles/motion'
import { formatTimestamp } from '../dates'
import { statusLabels } from '../presentation'
import type { LeaveRequest } from '../model'

export function RequestHistory({ request }: { request: LeaveRequest }) {
  const reduce = useReducedMotion()
  return <section className="request-history"><div className="section-heading"><div><span className="eyebrow">03 / ХРОНОЛОГИЯ</span><h2>История действий</h2></div><span className="history-count"><AnimatedValue value={request.history.length.toString().padStart(2, '0')} /></span></div>
    <ol><AnimatePresence initial={false}>{request.history.map((event) => <motion.li key={event.id} data-status={event.status}
      initial={reduce ? false : { opacity: 0.45, y: 8 }} animate={{ opacity: 1, y: 0 }}
      transition={reduce ? { duration: 0 } : { ...motionTokens.transition, delay: motionTokens.route.history }}>
      <span className="timeline-node" aria-hidden="true" /><div><time dateTime={event.occurredAt}>{formatTimestamp(event.occurredAt)}</time><h3>{event.status === 'Submitted' ? 'Заявка отправлена' : statusLabels[event.status]}</h3><span className="timeline-actor">{event.actorLabel}</span>{event.comment && <p>{event.comment}</p>}</div>
    </motion.li>)}</AnimatePresence></ol>
  </section>
}
