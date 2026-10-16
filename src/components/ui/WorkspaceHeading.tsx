import type { ReactNode } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { motionTokens } from '@/styles/motion'

export function WorkspaceHeading({ index, title, children }: { index: string; title: string; children?: ReactNode }) {
  const reduce = useReducedMotion()
  return <header className="workspace-page-heading"><p className="eyebrow">JANA FLOW <span>{index}</span></p><h1 className="editorial-title"><motion.span className="editorial-title-line" initial={reduce ? false : { y: '104%' }} animate={{ y: 0 }} transition={reduce ? { duration: 0 } : { duration: motionTokens.duration.expressive, ease: motionTokens.ease, delay: 0.04 }}>{title}<span className="heading-dot">.</span></motion.span></h1>{children && <motion.p initial={reduce ? false : { opacity: 0.5, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={reduce ? { duration: 0 } : { ...motionTokens.transition, delay: 0.08 }}>{children}</motion.p>}</header>
}
