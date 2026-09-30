export type AppRole = 'student' | 'instructor' | 'admin';
export type AppScreen = 'Dashboard'|'Knowledge Graph'|'Practice Session'|'Misconception Repair'|'Learning Path'|'Misconception Tracker'|'Analytics'|'Instructor'|'Admin/Ops'|'Edge-case States';

export function needsFastAnswerConfirmation(elapsedSeconds: number, acknowledged: boolean): boolean {
  return elapsedSeconds < 2 && !acknowledged;
}

export function shouldShowConfidenceReflection(confidence: number, mastery: number): boolean {
  return Math.abs(confidence / 5 - mastery) > .2;
}

export function canOpenScreen(role: AppRole, screen: AppScreen): boolean {
  if (screen === 'Instructor') return role === 'instructor' || role === 'admin';
  if (screen === 'Admin/Ops') return role === 'admin';
  return role === 'student';
}

export function reconnectDelay(attempt: number): number {
  return Math.min(1000 * 2 ** Math.max(0, attempt), 30000);
}

export type AnalyticsPeriod = '7d' | '30d' | 'all';
export function analyticsQuery(period: AnalyticsPeriod): string {
  return `?period=${encodeURIComponent(period)}`;
}

export type MisconceptionStatus = 'active'|'repairing'|'resolved'|'all';
export type MisconceptionSeverity = 'low'|'medium'|'high'|'all';
export function misconceptionQuery(status: MisconceptionStatus, severity: MisconceptionSeverity): string {
  const params = new URLSearchParams();
  if (status !== 'all') params.set('status', status);
  if (severity !== 'all') params.set('severity', severity);
  const value = params.toString();
  return value ? `?${value}` : '';
}
