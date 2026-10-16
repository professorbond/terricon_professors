import type { ReactNode } from 'react'
import { Button } from '@/components/ui/Button'
import { SegmentedControl } from '@/components/motion/SegmentedControl'
import type { ApiProblem } from '@/services/http/client'
import { setLang, useLang, useT, type Lang } from './i18n'
import './ext.css'

/** Состояния «загрузка / ошибка / пусто» в стиле экранов напарника. */
export function ExtState({ loading, problem, retry, empty, emptyTitle, emptyText, children }: {
  loading: boolean; problem: ApiProblem | null; retry: () => void; empty?: boolean; emptyTitle?: string; emptyText?: string; children?: ReactNode
}) {
  const t = useT()
  if (problem) return <div className="service-error" role="alert"><p>{problem.message || t('common.error')}</p><Button variant="secondary" onClick={retry}>{t('common.retry')}</Button></div>
  if (loading) return <p className="query-loading" role="status">{t('common.loading')}</p>
  if (empty) return <div className="register-empty ext-empty"><span aria-hidden="true">↗</span><h2>{emptyTitle ?? t('common.empty')}</h2>{emptyText && <p>{emptyText}</p>}</div>
  return <>{children}</>
}

export function LangSwitch() {
  const lang = useLang()
  const t = useT()
  return <div className="ext-lang"><SegmentedControl<Lang> label={t('common.lang')} value={lang} onChange={setLang} options={[{ value: 'ru', label: 'RU' }, { value: 'kk', label: 'KZ' }]} /></div>
}

export function Pill({ tone = 'neutral', children }: { tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info'; children: ReactNode }) {
  return <span className="ext-pill" data-tone={tone}>{children}</span>
}

/** Ошибка поля из ServiceProblem (fieldErrors) или общая. */
export function ProblemText({ problem, id }: { problem: ApiProblem | null; id?: string }) {
  if (!problem) return null
  return <p className="field-error" role="alert" id={id}>{problem.message}</p>
}
