import { useEffect, useRef } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { NotificationLink } from '@/features/notifications/NotificationLink'
import { Link, useLocation } from 'react-router'
import { PageTransition } from '@/components/motion/PageTransition'
import { Wordmark } from '@/components/brand/Wordmark'
import { getDemoRole } from '@/features/identity/demo-roles'
import type { Role } from '@/features/identity/model'
import { AppNavigation } from './components/AppNavigation'
import { UserMenu } from './components/UserMenu'
import { MobileNavigation } from './components/MobileNavigation'
import { supportNavigation } from './navigation'

export default function AppShell({ role }: { role: Role }) {
  const { pathname } = useLocation()
  const main = useRef<HTMLElement>(null)
  const previousPath = useRef<string | null>(null)
  const roleInfo = getDemoRole(role)
  const SupportIcon = supportNavigation.icon

  useEffect(() => {
    if (previousPath.current !== pathname) {
      main.current?.focus({ preventScroll: true })
      window.scrollTo({ top: 0, behavior: 'instant' })
      previousPath.current = pathname
    }
  }, [pathname])

  return (
    <div className="app-shell">
      <a href="#workspace-content" className="skip-link">Перейти к содержимому</a>
      <aside className="app-sidebar" aria-label="Панель рабочего пространства">
        <Link to={roleInfo.home} className="sidebar-brand" aria-label="JanaМен — начало"><Wordmark /></Link>
        <div className="sidebar-role"><span className="sidebar-role-index">{roleInfo.index}</span><div><span className="eyebrow">Ваше пространство</span><strong>{roleInfo.label}</strong></div></div>
        <AppNavigation role={role} />
        <div className="sidebar-bottom"><Link className="sidebar-support" to={supportNavigation.path}><SupportIcon size={20} strokeWidth={1.5} aria-hidden="true" /><span>{supportNavigation.label}<small>Спросите AI Jana</small></span><ArrowUpRight size={16} aria-hidden="true" /></Link><span className="sidebar-signature eyebrow">JANA FLOW <span>© 2026</span></span></div>
      </aside>
      <div className="app-workspace">
        <header className="workspace-header">
          <Link to={roleInfo.home} className="mobile-brand" aria-label="JanaМен — начало"><Wordmark /></Link>
          <div className="workspace-breadcrumb"><span className="workspace-location-dot" /><span>JanaМен</span><span className="breadcrumb-divider">/</span><strong>{roleInfo.description}</strong></div>
          <div className="workspace-tools"><span className="workspace-demo-tag">ДЕМО</span><NotificationLink /><span className="toolbar-divider" /><UserMenu role={role} /></div>
        </header>
        <main className="workspace-main" id="workspace-content" tabIndex={-1} ref={main}><PageTransition /></main>
        <footer className="workspace-footer"><span><span className="status-dot" /> Пространство для вашего рабочего дня</span><span className="eyebrow">J / M — {roleInfo.index}</span></footer>
      </div>
      <MobileNavigation role={role} />
    </div>
  )
}
