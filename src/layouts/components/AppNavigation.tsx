import { NavLink } from 'react-router'
import { useId } from 'react'
import { LayoutGroup, motion, useReducedMotion } from 'motion/react'
import { motionTokens } from '@/styles/motion'
import type { Role } from '@/features/identity/model'
import { getNavigation } from '../navigation'

export function AppNavigation({ role, onNavigate }: { role: Role; onNavigate?: () => void }) {
  const id = useId()
  const reduce = useReducedMotion()
  return (
    <LayoutGroup id={id}><nav className="app-navigation" aria-label="Основная навигация">
      {getNavigation(role).map((group) => (
        <div className="nav-group" key={group.label}>
          <p className="nav-group-label">{group.label}</p>
          <ul>
            {group.items.map(({ path, label, icon: Icon, index, end }) => (
              <li key={path}><NavLink to={path} end={end ?? false} onClick={onNavigate} className={({ isActive }) => `app-nav-link${isActive ? ' is-active' : ''}`}>
                {({ isActive }) => <>{isActive && <motion.span className="nav-motion-indicator" {...(!reduce ? { layoutId: 'active-route' } : {})} transition={reduce ? { duration: 0 } : motionTokens.spring} aria-hidden="true" />}<Icon size={19} strokeWidth={1.6} aria-hidden="true" /><span className="nav-label">{label}</span><span className="nav-index" aria-hidden="true">{index}</span></>}
              </NavLink></li>
            ))}
          </ul>
        </div>
      ))}
    </nav></LayoutGroup>
  )
}
