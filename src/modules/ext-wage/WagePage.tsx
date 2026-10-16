import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Check } from 'lucide-react'
import { WorkspaceHeading } from '@/components/ui/WorkspaceHeading'
import { Button } from '@/components/ui/Button'
import { SegmentedControl } from '@/components/motion/SegmentedControl'
import { api, type ApiProblem } from '@/services/http/client'
import { useApi } from '../ext-core/useApi'
import { useT } from '../ext-core/i18n'
import { money } from '../ext-core/format'
import { ExtState, LangSwitch } from '../ext-core/ui'
import type { Payslip, WageSummary, WithdrawOut } from './types'
import './i18n'

export default function WagePage() {
  const t = useT()
  const [tab, setTab] = useState<'get' | 'why'>('get')
  useEffect(() => { document.title = `${t('w.title')} · JanaМен` }, [t])
  return <div className="business-page">
    <WorkspaceHeading index={t('w.index')} title={t('w.title')}>{t('w.lead')}</WorkspaceHeading>
    <div className="ext-row ext-row--between"><div className="ext-tabs"><SegmentedControl<'get' | 'why'> label={t('w.title')} value={tab} onChange={setTab} options={[{ value: 'get', label: t('w.tab.get') }, { value: 'why', label: t('w.tab.why') }]} /></div><LangSwitch /></div>
    {tab === 'get' ? <GetMoney /> : <WhySoMuch />}
  </div>
}

function problemText(t: ReturnType<typeof useT>, p: ApiProblem, currency: string) {
  const data = p.data ?? {}
  if (p.code === 'AMOUNT_EXCEEDS_AVAILABLE') return t('errors.AMOUNT_EXCEEDS_AVAILABLE', { available: money(Number(data.available ?? 0), currency) })
  if (p.code === 'BELOW_MIN_AMOUNT') return t('errors.BELOW_MIN_AMOUNT', { min: money(Number(data.minAmount ?? 0), currency) })
  if (p.code === 'LIMIT_PER_PERIOD') return t('errors.LIMIT_PER_PERIOD')
  return p.message
}

function GetMoney() {
  const t = useT()
  const q = useApi<WageSummary>('/ext/wage/summary')
  const [amount, setAmount] = useState<string>('')
  const [problem, setProblem] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState<WithdrawOut | null>(null)
  const dialog = useRef<HTMLDialogElement>(null)
  const s = q.data
  const value = Number(amount || s?.available || 0)

  function ask(event: FormEvent) {
    event.preventDefault()
    if (!s) return
    if (value > s.available) { setProblem(t('errors.AMOUNT_EXCEEDS_AVAILABLE', { available: money(s.available, s.currency) })); return }
    if (value < s.minAmount) { setProblem(t('errors.BELOW_MIN_AMOUNT', { min: money(s.minAmount, s.currency) })); return }
    setProblem(null)
    dialog.current?.showModal()
  }
  async function confirm() {
    if (!s || busy) return
    setBusy(true)
    const r = await api.post<WithdrawOut>('/ext/wage/withdraw', { amount: value })
    setBusy(false)
    dialog.current?.close()
    if (r.ok) { setSent(r.data); setAmount('') } else setProblem(problemText(t, r.problem as ApiProblem, s.currency))
  }

  if (sent) return <section className="decision-complete ext-sent" role="status" data-testid="wage-sent"><Check size={22} aria-hidden="true" /><div>
    <h2>{t('w.sent.title')}</h2><p>{t('w.sent.text', { amount: money(sent.amount, sent.summary.currency) })}</p>
    <p className="ext-muted">{t('w.sent.request', { number: sent.requestNumber })}<br />{t('w.sent.doc', { number: sent.documentNumber })}</p>
    <Button variant="secondary" onClick={() => setSent(null)}>{t('w.sent.again')}</Button></div></section>

  return <ExtState loading={q.loading} problem={q.problem} retry={q.refresh}>{s && <>
    <section className="profile-overview ext-wage-hero"><div className="leave-balance"><span className="eyebrow">{t('w.available')}</span>
      <p className="ext-figure" data-testid="wage-available">{money(s.available, s.currency)}</p>
      <p className="ext-muted">{t('w.worked', { n: s.shiftsWorked, plan: s.shiftsPlanned, earned: money(s.earned, s.currency) })}</p></div>
      <dl className="request-facts"><div><dt>{t('w.facts.limit')}</dt><dd>{t('w.facts.limitValue', { pct: s.limitPct })}</dd></div><div><dt>{t('w.facts.withdrawn')}</dt><dd>{money(s.withdrawn, s.currency)}</dd></div><div><dt>{t('w.facts.left')}</dt><dd>{s.withdrawalsLeft} / {s.maxPerPeriod}</dd></div></dl></section>
    {s.available >= s.minAmount && s.withdrawalsLeft > 0 ? <form className="ext-form ext-section" onSubmit={ask} noValidate>
      <label><span>{t('w.amount')}</span><input inputMode="numeric" name="amount" aria-describedby="w-hint" value={amount} placeholder={String(s.available)} onChange={(e) => { setAmount(e.target.value.replace(/\D/g, '')); setProblem(null) }} /></label>
      <p id="w-hint" className="field-hint">{t('w.hint', { max: money(s.available, s.currency), min: money(s.minAmount, s.currency), left: s.withdrawalsLeft })}</p>
      <div className="ext-row"><Button variant="quiet" onClick={() => setAmount(String(Math.floor(s.available / 2)))}>{t('w.quick.half')}</Button><Button variant="quiet" onClick={() => setAmount(String(s.available))}>{t('w.quick.all')}</Button></div>
      {problem && <p className="field-error" role="alert">{problem}</p>}
      <div className="ext-actions"><Button type="submit">{t('w.getAmount', { amount: money(value, s.currency) })}</Button></div>
    </form> : <div className="register-empty ext-empty"><span aria-hidden="true">↗</span><h2>{t('w.none.title')}</h2><p>{t('w.none.text')}</p></div>}
    <dialog ref={dialog} className="confirmation-dialog" aria-labelledby="w-confirm">
      <h2 id="w-confirm">{t('w.confirm.title', { amount: money(value, s.currency) })}</h2><p>{t('w.confirm.text')}</p>
      <div className="dialog-actions"><Button variant="secondary" onClick={() => dialog.current?.close()}>{t('common.cancel')}</Button><Button onClick={() => void confirm()} disabled={busy} aria-busy={busy}>{busy ? t('common.sending') : t('w.confirm.ok')}</Button></div>
    </dialog>
  </>}</ExtState>
}

function WhySoMuch() {
  const t = useT()
  const q = useApi<Payslip>('/ext/wage/payslip-explained')
  const p = q.data
  return <ExtState loading={q.loading} problem={q.problem} retry={q.refresh}>{p && <section data-testid="wage-why">
    <span className="eyebrow">{t('w.why.period', { period: p.period })}</span>
    <div className="ext-table-scroll"><table className="ext-table"><tbody>
      {p.lines.map((l) => <tr key={l.code}><td>{l.label}</td><td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>{l.amount < 0 ? '− ' : ''}{money(Math.abs(l.amount), p.currency)}</td></tr>)}
      <tr><th scope="row">{t('w.why.gross')}</th><td style={{ textAlign: 'right' }}><strong>{money(p.gross, p.currency)}</strong></td></tr>
      <tr><th scope="row">{t('w.why.net')}</th><td style={{ textAlign: 'right' }}><strong>{money(p.net, p.currency)}</strong></td></tr>
      <tr><th scope="row">{t('w.why.received')}</th><td style={{ textAlign: 'right' }}>− {money(p.alreadyReceived, p.currency)}</td></tr>
      <tr><th scope="row">{t('w.why.toPay')}</th><td style={{ textAlign: 'right' }}><strong className="ext-figure ext-figure--ink" style={{ fontSize: '1.6rem' }}>{money(p.toBePaid, p.currency)}</strong></td></tr>
    </tbody></table></div>
    <p className="demo-footnote">{p.note}</p>
  </section>}</ExtState>
}
