import { useEffect } from 'react'
import { WorkspaceHeading } from '@/components/ui/WorkspaceHeading'
import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { ExtState, LangSwitch } from '../ext-core/ui'
import type { MyXray } from './types'
import './i18n'

/** Руководитель видит только свои метрики и место среди коллег — без чужих имён. */
export default function MyXrayPage() {
  const t = useT()
  const q = useApi<MyXray>('/ext/hr/xray/me')
  useEffect(() => { document.title = `${t('xr.me.title')} · JanaМен` }, [t])
  const m = q.data?.metrics
  return <div className="business-page">
    <WorkspaceHeading index="02 / КОМАНДА" title={t('xr.me.title')}>{t('xr.me.lead')}</WorkspaceHeading>
    <div className="ext-row ext-row--between"><span /><LangSwitch /></div>
    <ExtState loading={q.loading} problem={q.problem} retry={q.refresh}>{q.data && m && <>
      <p className="ext-figure ext-figure--ink" data-testid="xray-me">{q.data.slowerThanPct === null ? t('xr.me.noData') : q.data.slowerThanPct === 0 ? t('xr.me.faster') : t('xr.me.slower', { pct: q.data.slowerThanPct })}</p>
      <p className="ext-muted">{t('xr.me.rank', { rank: q.data.lateRank, total: q.data.peers + 1 })}</p>
      <div className="ext-grid ext-section">
        <div><span className="eyebrow">{t('xr.median')}</span><p className="ext-figure ext-figure--ink">{m.medianResponseHours === null ? '—' : t('xr.hours', { n: m.medianResponseHours })}</p></div>
        <div><span className="eyebrow">{t('xr.late')}</span><p className="ext-figure ext-figure--ink">{m.lateDecisions}</p></div>
        <div><span className="eyebrow">{t('xr.reject')}</span><p className="ext-figure ext-figure--ink">{m.rejectionShare === null ? '—' : `${Math.round(m.rejectionShare * 100)}%`}</p></div>
        <div><span className="eyebrow">{t('xr.pending')}</span><p className="ext-figure ext-figure--ink">{m.pendingNow}</p></div>
        <div><span className="eyebrow">{t('xr.atRisk')}</span><p className="ext-figure ext-figure--ink">{m.teamAtRisk}</p></div>
      </div>
    </>}</ExtState>
  </div>
}
