import { Link } from 'react-router'
import { WorkspaceHeading } from '@/components/ui/WorkspaceHeading'
import { QueryState } from '@/components/ui/QueryState'
import { useServices } from '@/services/context'
import { useServiceQuery } from '@/services/useServiceQuery'
import { formatDate } from '@/features/leave/dates'
import { ExtSlot } from '@/modules'

export default function ProfilePage() {
  const services = useServices()
  const query = useServiceQuery(services.profiles.getMyProfile)
  const profile = query.data
  return <div className="business-page"><WorkspaceHeading index="01 / ПРОФИЛЬ" title="Профиль сотрудника">Вымышленные данные для демонстрации сценария.</WorkspaceHeading>{profile ? <div className="profile-sheet"><h2>{profile.displayName}</h2><dl className="request-facts"><div><dt>Компания</dt><dd>{profile.company}</dd></div><div><dt>Должность</dt><dd>{profile.position}</dd></div><div><dt>Команда</dt><dd>{profile.department}</dd></div><div><dt>Руководитель</dt><dd>{profile.manager?.displayName ?? 'Не назначен'}</dd></div><div><dt>Дата начала работы</dt><dd>{formatDate(profile.hiredOn)}</dd></div><div><dt>Тестовый остаток</dt><dd>{profile.leaveBalance.days} календ. дн. на {formatDate(profile.leaveBalance.asOf)}</dd></div></dl><Link className="button button--primary" to="/requests/new/leave">Оформить отпуск</Link><p className="demo-footnote">Профиль доступен только для чтения. Остаток демонстрационный: уменьшается на календарные дни согласованных заявок.</p></div> : <QueryState problem={query.problem} retry={query.refresh} />}<ExtSlot name="profile.sections" /></div>
}
