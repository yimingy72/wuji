import { afterEach, expect, it, vi } from 'vitest';
import { criteriaText, goalTemplates } from '../src/goalTemplates';
import { creationIssues, scenarios } from '../src/domain';
import { getState, newDraft, reset, restoreGoal, saveDraft, setEntry, submit, switchScenario, updateContent, updateDraft } from '../src/store';

afterEach(() => { vi.useRealTimers(); reset(); });

it('switching scenarios preserves edited input and shares configuration without retaining scope confirmation', () => {
  reset();
  const initial = newDraft();
  const read = () => getState().drafts.find(d => d.id === initial.id)!;
  for (const scenario of scenarios) {
    switchScenario(initial.id, scenario.value);
    expect(read().content.objective).toBe(goalTemplates[scenario.value].objective);
    expect(read().completionCriteria).toBe(criteriaText(scenario.value));
  }
  switchScenario(initial.id, 'web_single');
  setEntry(initial.id, 'https://app.example.com');
  updateContent(initial.id, { objective: 'Custom Web goal', budget_usd: '3' });
  updateDraft(initial.id, {
    completionCriteria: 'Custom completion', supplementalHints: 'Known sign-in route',
    excludes: [{id:'exclude',host:'admin.example.com',descendants:true,endpoints:'all'}],
    validUntil:'2030-01-01T10:00:00Z', confirmed:true,
  });
  const before = structuredClone(read());
  switchScenario(initial.id, 'ctf');
  updateContent(initial.id, {challenge:'Challenge description', objective:'Custom CTF goal', budget_usd:'4'});
  switchScenario(initial.id, 'web_single');
  expect(read().content.objective).toBe('Custom Web goal');
  expect(read().completionCriteria).toBe('Custom completion');
  expect(read().includes).toEqual(before.includes);
  expect(read().excludes).toEqual(before.excludes);
  expect(read().validUntil).toBe(before.validUntil);
  expect(read().confirmed).toBe(false);
  expect(read().content.budget_usd).toBe('4');
  expect(read().supplementalHints).toBe('Known sign-in route');
  saveDraft(initial.id);
  expect(read().dirty).toBe(false);
  restoreGoal(initial.id);
  expect(read().content.objective).toBe(goalTemplates.web_single.objective);
  expect(read().completionCriteria).toBe(criteriaText('web_single'));
  expect(read().includes).toEqual(before.includes);
  switchScenario(initial.id, 'ctf');
  expect(read().content).toMatchObject({challenge:'Challenge description',objective:'Custom CTF goal'});
});

it('creation fixes the active goal and hints, and empty criteria only block creation', async () => {
  vi.useFakeTimers(); reset();
  const initial = newDraft();
  const read = () => getState().drafts.find(d => d.id === initial.id)!;
  setEntry(initial.id, 'https://app.example.com');
  updateContent(initial.id, {budget_usd:'2'});
  updateDraft(initial.id, {completionCriteria:'',validUntil:new Date(Date.now()+60_000).toISOString(),confirmed:true});
  saveDraft(initial.id);
  expect(read().dirty).toBe(false);
  expect(creationIssues(read(),getState().profiles)).toContain('请填写完成条件');
  updateDraft(initial.id,{completionCriteria:'Record actual findings and gaps',supplementalHints:'Focus on exports'});
  const request = submit(initial.id);
  await vi.advanceTimersByTimeAsync(500);
  const taskId = await request;
  expect(taskId).toBeTruthy();
  restoreGoal(initial.id);
  updateDraft(initial.id,{supplementalHints:'Later draft edit'});
  const task = getState().tasks.find(t => t.id === taskId)!;
  expect(task.draft.completionCriteria).toBe('Record actual findings and gaps');
  expect(task.draft.supplementalHints).toBe('Focus on exports');
  expect(task.draft.goalTemplate).toMatchObject({scenario:'web_single',version:1});
});
