import { AnimatePresence, motion, useIsPresent, useReducedMotion } from 'motion/react'
import { motionTokens } from '@/styles/motion'

function Value({ value }: { value: string | number }) {
  const present = useIsPresent()
  const reduce = useReducedMotion()
  return <motion.span className="animated-value-item" aria-hidden={!present || undefined}
    initial={reduce ? false : { opacity: 0, y: '45%' }} animate={{ opacity: 1, y: 0 }}
    exit={reduce ? { opacity: 0 } : { opacity: 0, y: '-35%' }}
    transition={reduce ? { duration: 0 } : motionTokens.transition}>{value}</motion.span>
}

/** A change of value, never a pretend intermediate business value. */
export function AnimatedValue({ value }: { value: string | number }) {
  return <span className="animated-value"><AnimatePresence initial={false} mode="sync"><Value key={value} value={value} /></AnimatePresence></span>
}
