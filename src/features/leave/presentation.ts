import type { LeaveRequest, LeaveStatus } from './model'

export const statusLabels: Record<LeaveStatus, string> = { Submitted: 'На согласовании', Approved: 'Согласовано', Rejected: 'Отклонено', Cancelled: 'Отменено', Escalated: 'Передано HR' }

export function nextStep(request: LeaveRequest) {
  if (request.status === 'Submitted') return `Решение: ${request.managerName}`
  if (request.status === 'Escalated') return 'Решение: HR'
  if (request.status === 'Rejected') return 'Ознакомиться с причиной'
  if (request.status === 'Approved') return 'Согласование завершено'
  return 'Заявка закрыта'
}
