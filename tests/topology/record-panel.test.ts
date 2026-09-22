import { describe, expect, test } from 'vitest';
import {
  parseRecordView,
  recordRequestPath,
  selectedRecordRef,
} from '../../apps/web/src/features/topology/record';
import { snapshot } from './fixtures';
import { summaryItems } from '../../apps/web/src/features/topology/panels/RecordPanel';

const ref = { entity_type: 'intent', id: 'intent / 1', revision: '7' } as const;

describe('record detail boundary', () => {
  test('run detail separates saved text, rejected semantics and a published checkpoint', () => {
    const items = summaryItems({
      process_state: 'unknown', raw_result_state: 'saved', result_state: 'rejected',
      checkpoint_state: 'published', checkpoint_ref: 'checkpoint-1',
    }, 'agent_run');
    expect(Object.fromEntries(items.map(item => [item.label, item.children]))).toEqual({
      '执行状态': '待核对', '原文留存': '已保存', '语义接纳': '已拒绝',
      '检查点': '已发布；恢复仍需平台核对当前权限和执行前沿', '检查点引用': 'checkpoint-1',
    });
  });

  test.each([{}, { raw_result_state: 'not_recorded', checkpoint_state: 'not_recorded' }])(
    'missing or unrecorded run facts do not imply failure or a completed stop: %j', facts => {
      const items = summaryItems({ ...facts, process_state: 'stopping', result_state: 'accepted' }, 'agent_run');
      expect(Object.fromEntries(items.map(item => [item.label, item.children]))).toEqual({
        '执行状态': '停止中，尚未确认退出', '原文留存': '未记录',
        '语义接纳': '已接纳', '检查点': '未记录',
      });
      expect(summaryItems({ state: 'cancelled' }, 'work_item')).toEqual([
        { key: 'state', label: 'state', children: 'cancelled' },
      ]);
    },
  );

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
