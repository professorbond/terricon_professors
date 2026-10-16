import { motion, useReducedMotion } from 'motion/react'
import { motionTokens } from '@/styles/motion'

export function FlowProgress({ value, total, label }: { value: number; total: number; label: string }) {
  const reduce = useReducedMotion()
  const progress = total > 0 ? Math.min(1, Math.max(0, value / total)) : 0
  return <div className="flow-progress" role="progressbar" aria-label={label} aria-valuenow={value} aria-valuemin={0} aria-valuemax={total}>
    <motion.span initial={false} animate={{ scaleX: progress }} transition={reduce ? { duration: 0 } : { duration: motionTokens.duration.expressive, ease: motionTokens.ease }} />
  </div>
}
