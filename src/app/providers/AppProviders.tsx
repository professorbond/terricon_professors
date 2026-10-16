import type { PropsWithChildren } from 'react'
import { MotionConfig } from 'motion/react'
import { BrowserRouter } from 'react-router'
import { motionTokens } from '@/styles/motion'
import { browserDemoSessionStore } from '@/mocks/demo-session'
import { DemoSessionProvider } from './DemoSessionProvider'
import { createMockServices } from '@/mocks/services'
import { apiEnabled } from '@/services/http/client'
import { createHttpServices } from '@/services/http/services'
import { ServicesContext } from '@/services/context'

// VITE_API_URL задан → реальный бэкенд; иначе — демо-моки (тесты Playwright напарника)
const services = apiEnabled ? createHttpServices(browserDemoSessionStore) : createMockServices(browserDemoSessionStore)

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <BrowserRouter>
      <MotionConfig reducedMotion="user" transition={motionTokens.transition}>
        <ServicesContext value={services}><DemoSessionProvider auth={services.auth}>{children}</DemoSessionProvider></ServicesContext>
      </MotionConfig>
    </BrowserRouter>
  )
}
