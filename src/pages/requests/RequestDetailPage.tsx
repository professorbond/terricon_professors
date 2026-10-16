import { RequestHistory } from '@/features/leave/components/RequestHistory'
import { useCallback } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { ArrowLeft } from 'lucide-react'
import { SubmissionConfirmation } from '@/features/leave/components/SubmissionConfirmation'
import { WorkspaceHeading } from '@/components/ui/WorkspaceHeading'
import { QueryState } from '@/components/ui/QueryState'
import { useServices } from '@/services/context'
import { useServiceQuery } from '@/services/useServiceQuery'
import { useDemoSession } from '@/features/identity/demo-context'
import { JanaFlowMap } from '@/features/leave/components/JanaFlowMap'
import { StatusBadge } from '@/features/leave/components/StatusBadge'
import { DecisionPanel } from '@/features/leave/components/DecisionPanel'
import { formatDate, formatTimestamp } from '@/features/leave/dates'
import { nextStep } from '@/features/leave/presentation'
import type { RequestOptions } from '@/services/contracts'

export default function RequestDetailPage({ manager = false }: { manager?: boolean }) {
  const { requestId = '' } = useParams()
  const [params] = useSearchParams()
  const { user } = useDemoSession()
  const services = useServices()
  const load = useCallback((options?: RequestOptions) => services.leaveRequests.getById(requestId, options), [services, requestId])
  const query = useServiceQuery(load)
  const request = query.data
  const canDecide = user?.role === 'Manager' && user.id === request?.managerId && user.id !== request?.employeeId
  return <div className="business-page"><Link className="back-link" to={manager ? '/manager/approvals' : '/requests'}><ArrowLeft size={16} aria-hidden="true" />{manager ? 'Очередь согласования' : 'Мои заявки'}</Link>
    <WorkspaceHeading index="L–01 / ОТПУСК" title={request?.number ?? 'Маршрут заявки'}>{request ? `${formatDate(request.startDate)} — ${formatDate(request.endDate)} · ${request.requestedDays} календ. дн.` : 'История и движение вашей заявки.'}</WorkspaceHeading>
    {!request ? <QueryState problem={query.problem} retry={query.refresh} /> : <>
      {params.get('created') === '1' && request.status === 'Submitted' && request.employeeId === user?.id && <SubmissionConfirmation request={request} />}
      <div className="request-status-line"><StatusBadge status={request.status} /><span>{nextStep(request)}</span><span className="eyebrow">ВЕРСИЯ {request.version.toString().padStart(2, '0')}</span></div>
      <div id="flow-map" tabIndex={-1}><JanaFlowMap request={request} /></div>
      {canDecide && <DecisionPanel key={request.id} request={request} />}
      <div className="request-detail-grid"><RequestHistory request={request} />
        <section className="request-details"><span className="eyebrow">04 / ДЕТАЛИ</span><h2>Всё о заявке</h2><dl className="request-facts"><div><dt>Тип</dt><dd>Отпуск</dd></div><div><dt>Сотрудник</dt><dd>{request.employeeName}</dd></div><div><dt>Период</dt><dd>{formatDate(request.startDate)} — {formatDate(request.endDate)}</dd></div><div><dt>Длительность</dt><dd>{request.requestedDays} календ. дн.</dd></div><div><dt>Согласующий</dt><dd>{request.managerName}</dd></div><div><dt>Создана</dt><dd>{formatTimestamp(request.createdAt)}</dd></div></dl>{request.comment && <div className="request-comment"><span className="eyebrow">КОММЕНТАРИЙ СОТРУДНИКА</span><p>{request.comment}</p></div>}<p className="demo-footnote">Все действия выполнены в демонстрационной системе. Даты и баланс не являются кадровым учётом.</p></section></div>
    </>}
  </div>
}
