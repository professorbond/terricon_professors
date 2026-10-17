import { useEffect, useState } from 'react'
import { WorkspaceHeading } from '@/components/ui/WorkspaceHeading'
import { Button } from '@/components/ui/Button'
import { SegmentedControl } from '@/components/motion/SegmentedControl'
import { api } from '@/services/http/client'
import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { keepMoneyTogether, money, shortDate } from '../ext-core/format'
import { featureEnabled } from '../ext-core/settings'
import { ExtState, LangSwitch, Pill } from '../ext-core/ui'
import { XrayTable } from './XrayTable'
import type { RiskCard, Savings, Signal } from './types'
import './i18n'

type Tab = 'radar' | 'xray'
type Country = 'KZ' | 'KG'

export default function HrConsolePage() {
  const t = useT()
  const [tab, setTab] = useState<Tab>(featureEnabled('hr_console') ? 'radar' : 'xray')
  const [country, setCountry] = useState<Country>('KZ')
  useEffect(() => { document.title = `${t('hr.title')} · JanaМен` }, [t])
  const tabs = [...(featureEnabled('hr_console') ? [{ value: 'radar' as Tab, label: t('hr.tab.radar') }] : []), ...(featureEnabled('xray') ? [{ value: 'xray' as Tab, label: t('hr.tab.xray') }] : [])]
  return <div className="business-page">
    <WorkspaceHeading index={t('hr.index')} title={t('hr.title')}>{t('hr.lead')}</WorkspaceHeading>
    <div className="ext-row ext-row--between">
      <div className="ext-row">{tabs.length > 1 && <div className="ext-tabs"><SegmentedControl<Tab> label={t('hr.title')} value={tab} onChange={setTab} options={tabs} /></div>}
        <div className="ext-tabs ext-tabs--small"><SegmentedControl<Country> label="Country" value={country} onChange={setCountry} options={[{ value: 'KZ', label: 'KZ' }, { value: 'KG', label: 'KG' }]} /></div></div>
      <LangSwitch />
    </div>
    {tab === 'radar' ? <Radar country={country} /> : <XrayTable country={country} />}
  </div>
}

function Radar({ country }: { country: Country }) {
  const t = useT()
  const risks = useApi<{ items: RiskCard[] }>(`/ext/hr/risks?country=${country}`)
  const savings = useApi<Savings>(`/ext/hr/savings?country=${country}`)
  const [busy, setBusy] = useState<string | null>(null)
  async function act(signal: Signal, action: 'propose-review' | 'confirm-retained') {
    setBusy(signal.id + action)
    await api.post(`/ext/hr/risks/${signal.id}/${action}`)
    setBusy(null)
  }
  return <>
    <section className="ext-panel ext-panel--dark ext-savings" data-testid="hr-savings" data-surface="dark">
      <ExtState loading={savings.loading} problem={savings.problem} retry={savings.refresh}>{savings.data && <>
        <span className="eyebrow">{t('hr.saved')} · {t('hr.savedPeople', { n: savings.data.retainedCount })}</span>
        <p className="ext-figure ext-savings-figure">{money(savings.data.saved, savings.data.currency)}</p>
        <p className="ext-muted">{t('hr.formula', { formula: savings.data.formula })}</p>
      </>}</ExtState>
    </section>
    <section className="ext-section"><div className="ext-row ext-row--between"><div><span className="eyebrow">{t('hr.atRisk')}</span><h2>{risks.data ? risks.data.items.length : '—'}</h2></div>
      <Button variant="quiet" onClick={() => void api.post(`/ext/hr/risks/recalculate?country=${country}`)}>{t('hr.recalc')}</Button></div>
      <ExtState loading={risks.loading} problem={risks.problem} retry={risks.refresh} empty={!!risks.data && !risks.data.items.length} emptyTitle={t('hr.noRisk')} emptyText={t('hr.noRiskText')}>
        <ul className="ext-list" data-testid="hr-risks">{risks.data?.items.map((c) => <li key={c.employeeId} className="ext-risk" data-employee={c.employeeId}>
          <div className="ext-risk-person"><strong>{c.employeeName}</strong><span className="ext-muted">{c.position} · {c.department}</span>{c.managerName && <span className="ext-muted">{t('hr.manager', { name: c.managerName })}</span>}
            {c.nextReviewDate && <Pill tone="success">{t('hr.reviewOn', { date: shortDate(c.nextReviewDate, true) })}</Pill>}</div>
          <ul className="ext-risk-signals">{c.signals.map((s) => <li key={s.id} data-kind={s.kind}>
            <div><p>{keepMoneyTogether(s.title)}</p><Pill tone={s.status === 'open' ? 'warning' : 'success'}>{t(`hr.status.${s.status}`)}</Pill></div>
            <div className="ext-actions">
              {s.status === 'open' && <Button variant="secondary" disabled={busy !== null} onClick={() => void act(s, 'propose-review')}>{t('hr.propose')}</Button>}
              {s.retainedConfirmed ? <Pill tone="success">{t('hr.retainedDone')}</Pill> : <Button variant="quiet" disabled={busy !== null} onClick={() => void act(s, 'confirm-retained')}>{t('hr.retained')}</Button>}
            </div>
          </li>)}</ul>
        </li>)}</ul>
      </ExtState>
    </section>
  </>
}
