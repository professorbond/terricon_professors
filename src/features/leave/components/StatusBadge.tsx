import type { LeaveStatus } from '../model'
import { statusLabels } from '../presentation'
import { AnimatedValue } from '@/components/motion/AnimatedValue'

export function StatusBadge({ status }: { status: LeaveStatus }) {
  return <span className="request-status" data-status={status}><span className="request-status-dot" aria-hidden="true" /><AnimatedValue value={statusLabels[status]} /></span>
}
