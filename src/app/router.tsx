import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router'
import { FoundationLayout } from '@/layouts/FoundationLayout'
import { FoundationPage } from '@/pages/foundation/FoundationPage'
import { PlannedPage } from '@/pages/planned/PlannedPage'
import { NotFoundPage } from '@/pages/not-found/NotFoundPage'
import { useDemoSession } from '@/features/identity/demo-context'
import { getDemoRole } from '@/features/identity/demo-roles'
import { plannedScreens, type PlannedScreen } from './routes'
import { extElement } from '@/modules'

const LoginPage = lazy(() => import('@/pages/login/LoginPage'))
const AppShell = lazy(() => import('@/layouts/AppShell'))
const DashboardPage = lazy(() => import('@/pages/dashboard/DashboardPage'))
const ProfilePage = lazy(() => import('@/pages/profile/ProfilePage'))
const LeavePage = lazy(() => import('@/pages/leave/LeavePage'))
const RequestsPage = lazy(() => import('@/pages/requests/RequestsPage'))
const RequestDetailPage = lazy(() => import('@/pages/requests/RequestDetailPage'))
const NotificationsPage = lazy(() => import('@/pages/notifications/NotificationsPage'))

function StartRoute() {
  const { role } = useDemoSession()
  return <Navigate to={role ? getDemoRole(role).home : '/login'} replace />
}

/** Demo routing convenience only. This cannot protect data or replace server RBAC. */
function DemoWorkspace() {
  const { role } = useDemoSession()
  return role ? <AppShell role={role} /> : <Navigate to="/login" replace />
}

function DemoScreen({ screen }: { screen: PlannedScreen }) {
  const { role } = useDemoSession()
  if (role && screen.roles.length > 0 && !screen.roles.includes(role)) return <Navigate to="/forbidden" replace />
  switch (screen.id) {
    case 'dashboard': return <DashboardPage />
    case 'profile': return <ProfilePage />
    case 'leave-new': return <LeavePage />
    case 'requests': return <RequestsPage />
    case 'request': return <RequestDetailPage />
    case 'approvals': return <RequestsPage manager />
    case 'approval': return <RequestDetailPage manager />
    case 'notifications': return <NotificationsPage />
  }
  return extElement(screen.id) ?? <PlannedPage screen={screen} />
}

export function AppRouter() {
  return (
    <Suspense fallback={<div className="route-loading" role="status">Открываем ваше пространство…</div>}>
      <Routes>
        <Route index element={<StartRoute />} />
        <Route path="/login" element={<LoginPage />} />
        {import.meta.env.DEV && <Route element={<FoundationLayout />}><Route path="/__foundation" element={<FoundationPage />} /></Route>}
        <Route element={<DemoWorkspace />}>
          {plannedScreens.filter((screen) => screen.id !== 'login').map((screen) => (
            <Route key={screen.id} path={screen.path} element={<DemoScreen screen={screen} />} />
          ))}
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
