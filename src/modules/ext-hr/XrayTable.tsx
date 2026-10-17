import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { ExtState, Pill } from '../ext-core/ui'
import type { ManagerMetrics } from './types'
import './i18n'

export function XrayTable({ country }: { country: string }) {
  const t = useT()
  const q = useApi<{ items: ManagerMetrics[] }>(`/ext/hr/xray?country=${country}`)
  const pct = (v: number | null) => (v === null ? '—' : `${Math.round(v * 100)}%`)
  return <section className="ext-section"><span className="eyebrow">{t('xr.title')}</span><p className="ext-muted">{t('xr.lead')}</p>
    <ExtState loading={q.loading} problem={q.problem} retry={q.refresh} empty={!!q.data && !q.data.items.length} emptyTitle={t('xr.empty')}>
      <div className="ext-table-scroll" role="region" aria-label={t('xr.title')} tabIndex={0}><table className="ext-table" data-testid="xray-table"><thead><tr>
        <th scope="col">{t('xr.manager')}</th><th scope="col">{t('xr.team')}</th><th scope="col">{t('xr.decided')}</th><th scope="col">{t('xr.median')}</th>
        <th scope="col">{t('xr.reject')}</th><th scope="col">{t('xr.late')}</th><th scope="col">{t('xr.pending')}</th><th scope="col">{t('xr.atRisk')}</th></tr></thead>
        <tbody>{q.data?.items.map((m) => <tr key={m.managerId}>
          <td><strong>{m.managerName}</strong><br /><span className="ext-muted">{m.department}</span></td><td>{m.teamSize}</td><td>{m.decided}</td>
          <td>{m.medianResponseHours === null ? '—' : t('xr.hours', { n: m.medianResponseHours })}</td><td>{pct(m.rejectionShare)}</td>
          <td>{m.lateDecisions ? <Pill tone="warning">{m.lateDecisions}</Pill> : 0}</td><td>{m.pendingNow}</td><td>{m.teamAtRisk ? <Pill tone="warning">{m.teamAtRisk}</Pill> : 0}</td>
        </tr>)}</tbody></table></div>
    </ExtState>
  </section>
}
