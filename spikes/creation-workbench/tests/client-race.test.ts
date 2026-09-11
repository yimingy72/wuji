import { afterEach, expect, it, vi } from 'vitest';
import { changeContext, newDraft, pending, reset, setEntry, submit, updateContent, updateDraft } from '../src/store';
function prepared() {
  const d=newDraft(); setEntry(d.id,'https://app.example.com');
  updateContent(d.id,{objective:'Synthetic fixture',budget_usd:'1'});
  updateDraft(d.id,{validUntil:new Date(Date.now()+86_400_000).toISOString(),confirmed:true});
  return d.id;
}
afterEach(()=>{vi.useRealTimers();reset();});
it('a late response from a previous identity cannot alter a new command for the same project',async()=>{
  vi.useFakeTimers();reset();
  const first=submit(prepared());
  await vi.advanceTimersByTimeAsync(100);
  changeContext('operator');changeContext('both');
  const second=submit(prepared());const key=pending()!.key;
  await vi.advanceTimersByTimeAsync(400);
  expect(await first).toBeNull();
  expect(pending()?.key).toBe(key);
  expect(pending()?.state).toBe('submitting');
  await vi.advanceTimersByTimeAsync(100);
  expect(await second).toBeTruthy();expect(pending()).toBeUndefined();
});
