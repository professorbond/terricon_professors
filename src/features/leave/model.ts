export type LeaveStatus = 'Submitted' | 'Approved' | 'Rejected' | 'Cancelled' | 'Escalated'

export interface LeaveRequestEvent {
  readonly id: string
  readonly status: LeaveStatus
  readonly occurredAt: string
  readonly actorLabel: string
  readonly actorId: string
  readonly comment: string | null
}

export type LeaveEvent = LeaveRequestEvent

export interface LeaveRequest {
  readonly id: string
  readonly number: string
  readonly type: 'Leave'
  readonly submissionKey: string
  readonly employeeId: string
  readonly employeeName: string
  readonly managerId: string
  readonly managerName: string
  /** Calendar dates YYYY-MM-DD; authoritative day count comes from the service. */
  readonly startDate: string
  readonly endDate: string
  readonly requestedDays: number
  readonly comment: string
  readonly status: LeaveStatus
  readonly createdAt: string
  readonly version: number
  readonly history: readonly LeaveEvent[]
}

export interface SubmitLeaveInput {
  readonly submissionKey: string
  readonly startDate: string
  readonly endDate: string
  readonly comment: string
}

export type LeaveDecision =
  | { readonly decision: 'Approved'; readonly expectedVersion: number; readonly comment?: string }
  | { readonly decision: 'Rejected'; readonly expectedVersion: number; readonly comment: string; readonly reasonCode?: string }
