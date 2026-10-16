import { Bell } from 'lucide-react'
import { useState } from 'react'
import { AnimatePresence } from 'motion/react'
import { AnimatedValue } from '@/components/motion/AnimatedValue'
import { NotificationSignal } from './NotificationSignal'
import { Link } from 'react-router'
import { useServices } from '@/services/context'
import { useServiceQuery } from '@/services/useServiceQuery'

export function NotificationLink() {
  const services = useServices()
  const query = useServiceQuery(services.notifications.listMine)
  const count = query.data?.items.filter((item) => !item.readAt).length ?? 0
  const [dismissed, setDismissed] = useState<readonly string[]>([])
  const incoming = query.data?.items.find((item) => !item.readAt && !dismissed.includes(item.id))
  const dismiss = () => { if (incoming) setDismissed((ids) => [...ids, incoming.id]) }
  return <><Link to="/notifications" className="notification-link icon-button" onClick={() => setDismissed(query.data?.items.map((item) => item.id) ?? [])} aria-label={query.problem ? 'Уведомления — не удалось обновить' : `Уведомления — ${count} новых`}><Bell size={21} strokeWidth={1.6} aria-hidden="true" /><span className="notification-count" data-unread={count > 0} aria-hidden="true"><AnimatedValue value={query.problem ? '!' : count > 99 ? '99+' : count} /></span><span className="sr-only" role="status">{count > 0 ? `Новых уведомлений: ${count}` : ''}</span></Link><AnimatePresence>{incoming && <NotificationSignal key={incoming.id} notification={incoming} onDismiss={dismiss} />}</AnimatePresence></>
}
