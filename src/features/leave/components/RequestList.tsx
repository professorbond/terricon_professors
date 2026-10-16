import { useState } from 'react'
import { Link } from 'react-router'
import { ArrowUpRight, Search } from 'lucide-react'
import type { LeaveRequest } from '../model'
import { formatDate, todayDate } from '../dates'
import { nextStep } from '../presentation'
import { StatusBadge } from './StatusBadge'
import { ExtSlot } from '@/modules'

export function RequestList({ requests, manager = false }: { requests: readonly LeaveRequest[]; manager?: boolean }) {
  const [status, setStatus] = useState(manager ? 'Submitted' : 'all')
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('newest')
  const filtered = requests.filter((request) => (status === 'all' || request.status === status) && `${request.number} ${request.employeeName}`.toLocaleLowerCase('ru').includes(search.trim().toLocaleLowerCase('ru')))
    .sort((a, b) => sort === 'start' ? a.startDate.localeCompare(b.startDate) || a.number.localeCompare(b.number) : (a.createdAt.localeCompare(b.createdAt) || a.number.localeCompare(b.number)) * (sort === 'oldest' ? 1 : -1))
  return <div className="requests-register">
    <div className="register-toolbar"><label className="register-search"><span className="sr-only">Поиск заявки</span><Search size={17} aria-hidden="true" /><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder={manager ? 'Номер или сотрудник' : 'Номер заявки'} /></label>
      <label className="register-control"><span>Статус</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">Все статусы</option><option value="Submitted">На согласовании</option><option value="Approved">Согласовано</option><option value="Rejected">Отклонено</option></select></label>
      <label className="register-control"><span>Сортировка</span><select value={sort} onChange={(event) => setSort(event.target.value)}><option value="newest">Сначала новые</option><option value="oldest">Сначала ранние</option><option value="start">По началу отпуска</option></select></label>
    </div>
    <p className="register-count eyebrow" role="status">Найдено заявок: {filtered.length}</p>
    {filtered.length ? <div className="request-table-scroll" tabIndex={0} role="region" aria-label="Реестр заявок"><table className="request-table"><caption className="sr-only">{manager ? 'Заявки вашей команды' : 'Ваши заявки на отпуск'}</caption><thead><tr><th scope="col">Заявка / тип</th><th scope="col">{manager ? 'Сотрудник / период' : 'Период / дни'}</th><th scope="col">Создана</th><th scope="col">Статус</th><th scope="col">Следующий шаг</th></tr></thead><tbody>{filtered.map((request) => <tr key={request.id}>
      <td><Link className="request-number" to={`${manager ? '/manager/approvals' : '/requests'}/${request.id}`}>{request.number}<ArrowUpRight size={15} aria-hidden="true" /></Link><small>Отпуск</small></td>
      <td>{manager && <strong className="request-employee">{request.employeeName}</strong>}<span>{formatDate(request.startDate)} —<br />{formatDate(request.endDate)}</span>{!manager && <small>{request.requestedDays} календ. дн.</small>}</td>
      <td>{formatDate(todayDate(new Date(request.createdAt)))}</td><td><StatusBadge status={request.status} /><ExtSlot name="request.list.badge" requestId={request.id} /></td><td className="request-next-step">{nextStep(request)}</td>
    </tr>)}</tbody></table></div> : <div className="register-empty"><span aria-hidden="true">↗</span><h2>{requests.length ? 'Нет совпадений' : manager ? 'В команде пока нет заявок' : 'Первый маршрут начинается с вас'}</h2><p>{requests.length ? 'Измените поиск или выбранный статус.' : manager ? 'Отправьте заявку из демо-профиля сотрудника. Она появится здесь.' : 'Оформите отпуск — здесь появятся номер, статус и следующий шаг.'}</p></div>}
  </div>
}
