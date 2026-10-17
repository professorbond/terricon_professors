import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { featureEnabled } from '../ext-core/settings'
import { Pill } from '../ext-core/ui'
import type { CourseTag } from './types'
import './i18n'

/** Бейдж «Нужен для грейда SORT-2» (данные лестницы; без фичи ladder — ничего). */
export function GradeTag({ courseId }: { courseId: string }) {
  const t = useT()
  const tags = useApi<CourseTag[]>(featureEnabled('ladder') ? '/ext/ladder/course-tags' : null)
  const grades = tags.data?.find((x) => x.courseId === courseId)?.grades ?? []
  if (!grades.length) return null
  return <span className="ext-badges" data-testid="grade-tag">{grades.map((g) => <Pill key={g.code} tone="info">{t('ac.forGrade', { grade: g.code })}</Pill>)}</span>
}
