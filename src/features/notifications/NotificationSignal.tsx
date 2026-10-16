import { motion, useIsPresent, useReducedMotion } from 'motion/react'
import { ArrowUpRight, X } from 'lucide-react'
import { Link } from 'react-router'
import type { Notification } from './model'
import { motionTokens } from '@/styles/motion'

export function NotificationSignal({ notification, onDismiss }: { notification: Notification; onDismiss: () => void }) {
  const reduce = useReducedMotion()
  const present = useIsPresent()
  const target = notification.target.kind === 'request' ? `/requests/${notification.target.requestId}` : `/academy/${notification.target.courseId}`
  return <motion.aside className="notification-signal" aria-label="Новое уведомление" aria-hidden={!present || undefined} inert={!present}
    initial={reduce ? false : { opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
    transition={reduce ? { duration: 0 } : motionTokens.transition}>
    <div><span className="eyebrow">НОВЫЙ СИГНАЛ / ВХОДЯЩИЕ</span><p>{notification.title}</p><Link to={target} className="text-link" onClick={onDismiss}>Открыть результат <ArrowUpRight size={15} aria-hidden="true" /></Link></div>
    <button type="button" className="icon-button" aria-label="Закрыть уведомление" onClick={onDismiss}><X size={17} /></button>
  </motion.aside>
}
