import { useEffect, useState } from 'react'
import { WorkspaceHeading } from '@/components/ui/WorkspaceHeading'
import { Button } from '@/components/ui/Button'
import { SegmentedControl } from '@/components/motion/SegmentedControl'
import { api, type ApiProblem } from '@/services/http/client'
import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { ExtState, LangSwitch, Pill } from '../ext-core/ui'
import './i18n'

interface Policy {
  id: number; country: string; requestType: string; slaHours: number | null; onTimeout: 'auto_approve' | 'escalate_hr' | null; enabled: boolean
  wageLimitPct: number | null; wageMaxPerPeriod: number | null; wageMinAmount: number | null; reviewPeriodMonths: number | null; replacementCostPct: number | null; avgAnnualSalary: number | null
}
type Country = 'KZ' | 'KG'
const NUM: (keyof Policy)[] = ['slaHours', 'wageLimitPct', 'wageMaxPerPeriod', 'wageMinAmount', 'reviewPeriodMonths', 'replacementCostPct', 'avgAnnualSalary']

export default function PoliciesPage() {
  const t = useT()
  const [country, setCountry] = useState<Country>('KZ')
  const q = useApi<Policy[]>(`/ext/policies?country=${country}`)
  useEffect(() => { document.title = `${t('p.title')} · JanaМен` }, [t])
  return <div className="business-page">
    <WorkspaceHeading index={t('p.index')} title={t('p.title')}>{t('p.lead')}</WorkspaceHeading>
    <div className="ext-row ext-row--between"><div className="ext-tabs ext-tabs--small"><SegmentedControl<Country> label={t('p.country')} value={country} onChange={setCountry} options={[{ value: 'KZ', label: 'KZ' }, { value: 'KG', label: 'KG' }]} /></div><LangSwitch /></div>
    <ExtState loading={q.loading} problem={q.problem} retry={q.refresh} empty={!!q.data && !q.data.length}>
      <ul className="ext-list" data-testid="policies">{q.data?.map((p) => <PolicyRow key={`${p.id}-${country}`} policy={p} />)}</ul>
    </ExtState>
  </div>
}

function PolicyRow({ policy }: { policy: Policy }) {
  const t = useT()
  const [draft, setDraft] = useState<Policy>(policy)
  const [state, setState] = useState<{ saved?: boolean; problem?: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const type = policy.requestType
  const isCountry = type === '*'
  const isWage = type === 'wage_access'
  const num = (key: keyof Policy, label: string) => <label key={key}><span>{label}</span><input inputMode="numeric" value={draft[key] === null ? '' : String(draft[key])} onChange={(e) => { setDraft({ ...draft, [key]: e.target.value === '' ? null : Number(e.target.value.replace(/\D/g, '')) }); setState(null) }} /></label>
  async function save() {
    setBusy(true)
    const body = Object.fromEntries(Object.entries(draft).filter(([k, v]) => k !== 'id' && k !== 'country' && k !== 'requestType' && k !== 'updatedAt' && (v !== null || !NUM.includes(k as keyof Policy))))
    const r = await api.put<Policy>(`/ext/policies/${policy.id}`, body)
    setBusy(false)
    if (r.ok) setState({ saved: true })
    else setState({ problem: (r.problem as ApiProblem).code === 'AUTO_APPROVE_FORBIDDEN' ? t('errors.AUTO_APPROVE_FORBIDDEN') : r.problem.message })
  }
  return <li className="ext-policy" data-type={type}>
    <div><strong>{t(`p.t.${type}`)}</strong><span className="ext-muted">{type}</span>{!draft.enabled && <Pill tone="warning">off</Pill>}</div>
    <div className="ext-form ext-policy-fields">
      {!isCountry && !isWage && <>{num('slaHours', t('p.sla'))}
        <label><span>{t('p.timeout')}</span><select value={draft.onTimeout ?? ''} onChange={(e) => { setDraft({ ...draft, onTimeout: (e.target.value || null) as Policy['onTimeout'] }); setState(null) }}><option value="">{t('p.none')}</option><option value="auto_approve">{t('p.auto_approve')}</option><option value="escalate_hr">{t('p.escalate_hr')}</option></select></label></>}
      {isWage && <>{num('wageLimitPct', t('p.limit'))}{num('wageMaxPerPeriod', t('p.maxPer'))}{num('wageMinAmount', t('p.min'))}
        <label><span>{t('p.timeout')}</span><select value={draft.onTimeout ?? ''} onChange={(e) => { setDraft({ ...draft, onTimeout: (e.target.value || null) as Policy['onTimeout'] }); setState(null) }}><option value="">{t('p.none')}</option><option value="auto_approve">{t('p.auto_approve')}</option><option value="escalate_hr">{t('p.escalate_hr')}</option></select></label></>}
      {isCountry && <>{num('reviewPeriodMonths', t('p.review'))}{num('replacementCostPct', t('p.replace'))}{num('avgAnnualSalary', t('p.avg'))}</>}
      {!isCountry && <label className="ext-check"><input type="checkbox" checked={draft.enabled} onChange={(e) => { setDraft({ ...draft, enabled: e.target.checked }); setState(null) }} />{t('p.enabled')}</label>}
    </div>
    <div className="ext-actions"><Button variant="secondary" onClick={() => void save()} disabled={busy} aria-busy={busy}>{t('p.save')}</Button>
      {state?.saved && <span role="status" className="ext-muted">{t('p.saved')}</span>}{state?.problem && <p className="field-error" role="alert">{state.problem}</p>}</div>
  </li>
}
