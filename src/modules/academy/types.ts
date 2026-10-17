export interface Progress { courseId: string; completedLessonIds: string[]; totalLessons: number; status: 'Assigned' | 'InProgress' | 'Completed'; scorePercent: number | null; passed: boolean; lessonsPercent: number }
export interface CourseSummary { id: string; title: string; description: string; durationMinutes: number }
export interface Assigned extends CourseSummary { assignedAt: string; dueDate: string | null; progress: Progress }
export interface CourseDetail extends CourseSummary { passingScore: number; assigned: boolean; lessons: { id: string; ord: number; title: string; contentMd: string; completed: boolean }[]; questions: { id: string; ord: number; text: string; options: string[] }[]; progress: Progress | null }
export interface CourseTag { courseId: string; grades: { code: string; title: string }[] }
export interface SubmitOut { score: number; passed: boolean; passingScore: number; correct: number; total: number; progress: Progress }
