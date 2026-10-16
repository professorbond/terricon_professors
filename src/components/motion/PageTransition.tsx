import { Suspense, type PropsWithChildren } from 'react'
import { AnimatePresence, motion, useIsPresent, useReducedMotion } from 'motion/react'
import { useLocation, useOutlet } from 'react-router'
import { motionTokens } from '@/styles/motion'

function PageFrame({ children }: PropsWithChildren) {
  const present = useIsPresent()
  const reduce = useReducedMotion()
  return <motion.div className="route-frame" data-present={present} inert={!present} aria-hidden={!present || undefined}
    initial={reduce ? false : { opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
    exit={reduce ? { opacity: 0 } : { opacity: 0, y: -4, transition: { duration: motionTokens.duration.fast } }}
    transition={reduce ? { duration: 0 } : { ...motionTokens.transition, delay: 0.06 }}>
    <Suspense fallback={<p className="workspace-pending" role="status">Открываем раздел…</p>}>{children}</Suspense>
  </motion.div>
}

/** The outlet snapshot retains the old route's params while it exits. Shell stays mounted. */
export function PageTransition() {
  const { pathname } = useLocation()
  const outlet = useOutlet()
  return <div className="route-stage"><AnimatePresence initial={false} mode="sync"><PageFrame key={pathname}>{outlet}</PageFrame></AnimatePresence></div>
}
