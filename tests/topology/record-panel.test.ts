import { describe, expect, test } from 'vitest';
import {
  parseRecordView,
  recordRequestPath,
  selectedRecordRef,
} from '../../apps/web/src/features/topology/record';
import { snapshot } from './fixtures';

const ref = { entity_type: 'intent', id: 'intent / 1', revision: '7' } as const;

describe('record detail boundary', () => {
  test('request path binds the exact revision and snapshot', () => {
    const url = new URL(
      recordRequestPath('task / 1', ref, 'snapshot / 3'),
      'https://wuji.invalid',
    );
    expect(url.pathname).toBe('/api/v2/tasks/task%20%2F%201/records/intent/intent%20%2F%201');
    expect(Object.fromEntries(url.searchParams)).toEqual({
      revision: '7',
      snapshot_id: 'snapshot / 3',
    });
  });

  test('record parser rejects a response for another revision', () => {
    const value = {
      assessment: null,
      ref,
      display_kind: 'intent',
      record: { question: 'fixed question', acceptance_state: 'admitted' },
    };
    expect(parseRecordView(value, ref)).toEqual(value);
    expect(() => parseRecordView(value, { ...ref, revision: '8' })).toThrow(
      '记录响应不符合固定契约',
    );
  });

  test('follow-latest selection resolves to the exact visible node revision', () => {
    expect(selectedRecordRef(snapshot, {
      mode: 'follow_latest',
      anchor: { entity_type: 'claim', id: 'claim-1' },
    })).toEqual({ entity_type: 'claim', id: 'claim-1', revision: '2' });
  });
});
