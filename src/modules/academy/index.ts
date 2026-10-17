import { lazy } from 'react'
import { BookOpen } from 'lucide-react'
import type { ExtModule } from '../ext-core/registry'

const ALL = ['Employee', 'Manager', 'HRAdmin'] as const

/** Экраны Academy вместо заглушек напарника (academy, course, lesson, result, hr-learning) + обучение команды руководителю. */
export const academyModule: ExtModule = {
  id: 'academy',
  screens: [
    { id: 'academy', titleKey: 'ac.title', roles: ALL, component: lazy(() => import('./AcademyPage')) },
    { id: 'course', titleKey: 'ac.title', roles: ALL, component: lazy(() => import('./CoursePage')) },
    { id: 'lesson', titleKey: 'ac.title', roles: ALL, component: lazy(() => import('./LessonPage')) },
    { id: 'result', titleKey: 'ac.test', roles: ALL, component: lazy(() => import('./ResultPage')) },
    { id: 'hr-learning', titleKey: 'ac.hr.title', roles: ['HRAdmin'], component: lazy(() => import('./LearningAdminPage')) },
    { id: 'ext-team-learning', path: '/manager/learning', titleKey: 'ac.hr.title', roles: ['Manager'], component: lazy(() => import('./LearningAdminPage')) },
  ],
  nav: [{ path: '/manager/learning', labelKey: 'ac.hr.title', icon: BookOpen, roles: ['Manager'] }],
}
