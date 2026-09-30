import { describe, expect, it } from 'vitest';

function calibration(confidence:number, mastery:number){const gap=confidence/5-mastery;return gap>.2?'overconfident':gap<-.2?'underconfident':'calibrated'}
describe('confidence calibration bands',()=>{
 it('detects overconfidence',()=>expect(calibration(5,.2)).toBe('overconfident'));
 it('detects underconfidence',()=>expect(calibration(1,.8)).toBe('underconfident'));
 it('labels small gaps calibrated',()=>expect(calibration(3,.6)).toBe('calibrated'));
});
