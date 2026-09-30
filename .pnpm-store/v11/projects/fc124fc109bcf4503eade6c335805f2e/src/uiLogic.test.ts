import { describe, expect, it } from 'vitest';
import { analyticsQuery, canOpenScreen, misconceptionQuery, needsFastAnswerConfirmation, reconnectDelay, shouldShowConfidenceReflection } from './uiLogic';

describe('fast-answer nudge',()=>{
  it('nudges for a response under two seconds',()=>expect(needsFastAnswerConfirmation(1.99,false)).toBe(true));
  it('does not nudge at two seconds',()=>expect(needsFastAnswerConfirmation(2,false)).toBe(false));
  it('respects explicit confirmation',()=>expect(needsFastAnswerConfirmation(.2,true)).toBe(false));
});
describe('confidence reflection',()=>{
  it('prompts for high confidence against low mastery',()=>expect(shouldShowConfidenceReflection(5,.2)).toBe(true));
  it('prompts for low confidence against high mastery',()=>expect(shouldShowConfidenceReflection(1,.8)).toBe(true));
  it('does not prompt for close evidence',()=>expect(shouldShowConfidenceReflection(3,.6)).toBe(false));
});
describe('role route guards',()=>{
  it('keeps student screens student-only',()=>expect(canOpenScreen('instructor','Analytics')).toBe(false));
  it('allows an instructor to open instructor tools',()=>expect(canOpenScreen('instructor','Instructor')).toBe(true));
  it('keeps admin tools admin-only',()=>expect(canOpenScreen('instructor','Admin/Ops')).toBe(false));
  it('allows admins to inspect instructor tools',()=>expect(canOpenScreen('admin','Instructor')).toBe(true));
});
describe('SSE reconnect backoff',()=>{
  it('starts at one second and doubles',()=>expect([reconnectDelay(0),reconnectDelay(1),reconnectDelay(2)]).toEqual([1000,2000,4000]));
  it('caps at thirty seconds',()=>expect(reconnectDelay(10)).toBe(30000));
});
describe('analytics period filters',()=>{
  it('queries the seven-day window',()=>expect(analyticsQuery('7d')).toBe('?period=7d'));
  it('queries the thirty-day window',()=>expect(analyticsQuery('30d')).toBe('?period=30d'));
  it('queries all time',()=>expect(analyticsQuery('all')).toBe('?period=all'));
});
describe('misconception filters',()=>{
  it('serializes status and severity for server filtering',()=>expect(misconceptionQuery('active','high')).toBe('?status=active&severity=high'));
  it('omits unfiltered values',()=>expect(misconceptionQuery('all','all')).toBe(''));
});
