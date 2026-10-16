import { useId, useState, type CSSProperties } from 'react'
import { Check, ArrowUpRight, X, ArrowDownRight } from 'lucide-react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { useDemoSession } from '@/features/identity/demo-context'
import { FlowProgress } from '@/components/motion/FlowProgress'
import { motionTokens } from '@/styles/motion'
import { useLivingRoute } from '../motion/useLivingRoute'
import { routeGeometry } from '../motion/routeGeometry'
import { formatTimestamp } from '../dates'
import type { LeaveRequest } from '../model'

export function JanaFlowMap({ request, compact = false }: { request: LeaveRequest; compact?: boolean }) {
  const pending = request.status === 'Submitted'
  const approved = request.status === 'Approved'
  const rejected = request.status === 'Rejected'
  const { user } = useDemoSession()
  const reduce = useReducedMotion()
  const event = request.history.at(-1)
  const root = useLivingRoute(`${user?.id}/${request.id}/${event?.id ?? request.version}`)
  const cardId = useId()
  const [inspection, setInspection] = useState<{ requestId: string; version: number; index: number } | null>(null)
  const selected = inspection?.requestId === request.id && inspection.version === request.version ? inspection.index : pending ? 1 : 2
  const nodes = [
    { title: 'Отправлено', person: request.employeeName, state: 'done', caption: 'Заявка зарегистрирована', detail: `Маршрут открыт ${formatTimestamp(request.createdAt)}. Период и комментарий переданы руководителю.` },
    { title: pending ? 'У руководителя' : approved ? 'Согласовано' : rejected ? 'Отклонено' : 'Отменено', person: request.managerName, state: pending ? 'current' : approved ? 'done' : 'rejected', caption: pending ? 'Согласование · ожидает решения' : 'Решение записано в историю', detail: pending ? 'Следующее действие — согласовать заявку или отклонить её с причиной. Уведомление появится после решения.' : event?.comment || 'Руководитель подтвердил решение. Запись сохранена в истории заявки.' },
    { title: pending ? 'Ваш результат' : approved ? 'Согласована' : rejected ? 'Отклонена' : 'Отменена', person: request.employeeName, state: pending ? 'waiting' : 'done', caption: pending ? 'После решения руководителя' : 'Уведомление создано', detail: pending ? 'Этот участок ещё не пройден. Здесь появится результат согласования.' : approved ? 'Отпуск согласован в демо-системе. Тестовый остаток обновлён, уведомление доступно сотруднику.' : event?.comment || 'Заявка закрыта. Тестовый остаток не изменён.' },
  ]
  const stage = nodes[selected] ?? nodes[1]!
  return <section ref={root} className={`jana-flow-map living-route ${compact ? 'jana-flow-map--compact' : ''}`} data-surface="dark" data-status={request.status} data-tone={rejected ? 'warm' : 'normal'} aria-label="Jana Flow Map">
    <div className="flow-map-heading"><span className="eyebrow">JANA FLOW MAP <span>/ L–01</span></span><span className="flow-map-live"><span />{pending ? 'Маршрут активен' : 'Маршрут завершён'}</span></div>
    <div className="route-graphic">
      {(['horizontal', 'vertical'] as const).map((layout) => {
        const geometry = routeGeometry[layout]
        const route = rejected ? geometry.rejection : geometry.approved
        return <svg key={layout} data-layout={layout} className="route-svg" viewBox={`0 0 ${geometry.width} ${geometry.height}`} preserveAspectRatio="none" aria-hidden="true">
          <path className="route-track" d={geometry.submitted} /><path className="route-track route-track--future" d={geometry.approved} /><path className="route-track route-track--alternative" d={geometry.rejection} />
          <path className="route-segment js-route-segment" d={geometry.submitted} data-active={pending} data-confirmed="true" />
          <path className="route-segment route-segment--outcome js-route-segment" d={route} data-active={!pending} data-confirmed={!pending} />
          <g className="js-route-signal route-signal"><circle r="12" className="route-signal-halo" /><circle r="4" className="route-signal-core" /></g>
        </svg>
      })}
      <span className="route-coordinate route-coordinate--start" aria-hidden="true">01 / ОТПРАВКА</span>
      <span className="route-branch-label" aria-hidden="true">{rejected ? 'R / ПРИЧИНА СОХРАНЕНА' : 'R / ВЕТКА ОТКЛОНЕНИЯ'}</span>
      <ol className="flow-stations">{nodes.map((node, index) => {
        const h = rejected && index === 2 ? routeGeometry.horizontal.rejected : routeGeometry.horizontal.points[index]!
        const v = rejected && index === 2 ? routeGeometry.vertical.rejected : routeGeometry.vertical.points[index]!
        const position = { '--station-x': `${h[0] / 10}%`, '--station-y': `${h[1] / 3}%`, '--station-mobile-x': `${v[0] / 3.2}%`, '--station-mobile-y': `${v[1] / 4.3}%` } as CSSProperties
        return <li key={index} style={position} data-state={node.state} data-arrival={index === (pending ? 1 : 2)} aria-current={node.state === 'current' ? 'step' : undefined}>
          <button type="button" className="route-station-button" aria-pressed={selected === index} aria-controls={cardId} onClick={() => setInspection({ requestId: request.id, version: request.version, index })}>
            <span className="flow-station-mark" aria-hidden="true"><span className="route-arrival" />{node.state === 'rejected' || (rejected && index === 2) ? <X size={17} /> : node.state === 'done' ? <Check size={17} /> : node.state === 'current' ? <ArrowUpRight size={17} /> : '03'}</span>
            <span className="route-station-copy"><span className="flow-station-index">0{index + 1} / {node.state === 'current' ? 'СЕЙЧАС' : node.state === 'waiting' ? 'ДАЛЕЕ' : 'ПРОЙДЕНО'}</span><span className="route-station-title">{node.title}</span><span className="route-station-person">{node.person}</span><span className="route-station-caption">{node.caption}</span></span>
          </button>
        </li>
      })}</ol>
    </div>
    <div className="route-stage-card" id={cardId}><span className="route-card-index" aria-hidden="true">0{selected + 1}<ArrowDownRight size={23} strokeWidth={1.3} /></span><AnimatePresence initial={false} mode="wait"><motion.div className="route-card-copy" key={`${selected}-${request.status}`} initial={reduce ? false : { opacity: 0.4, x: 5 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, transition: { duration: reduce ? 0 : 0.1 } }} transition={reduce ? { duration: 0 } : motionTokens.transition}><span className="eyebrow">{selected === (pending ? 1 : 2) ? 'ТЕКУЩИЙ ЭТАП' : 'СТАНЦИЯ МАРШРУТА'}</span><h3>{stage.title}</h3><p>{stage.detail}</p></motion.div></AnimatePresence></div>
    <div className="route-footer"><span className="eyebrow">{request.number}</span><span>Этап {pending ? '2' : '3'} из 3</span><FlowProgress value={pending ? 2 : 3} total={3} label="Этапы маршрута заявки" /></div>
  </section>
}
