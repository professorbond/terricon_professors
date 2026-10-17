export interface Signal { id: string; kind: string; title: string; status: 'open' | 'actioned' | 'resolved'; retainedConfirmed: boolean; detectedAt: string }
export interface RiskCard { employeeId: string; employeeName: string; position: string; department: string; country: string; managerName: string | null; openSignals: number; signals: Signal[]; nextReviewDate: string | null }
export interface Savings { country: string; currency: string; retainedCount: number; perPerson: number; saved: number; formula: string }
export interface ManagerMetrics { managerId: string; managerName: string; department: string; country: string; teamSize: number; decided: number; medianResponseHours: number | null; rejectionShare: number | null; lateDecisions: number; pendingNow: number; teamAtRisk: number }
export interface MyXray { metrics: ManagerMetrics; peers: number; slowerThanPct: number | null; lateRank: number }
