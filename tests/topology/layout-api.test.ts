import { describe, expect, test } from 'vitest';
import {
  LayoutRequestError,
  layoutPatch,
  layoutRequestPath,
  layoutViewName,
  parseLayoutPreference,
} from '../../apps/web/src/features/topology/layoutApi';
import { layout } from './fixtures';

describe('personal layout API boundary', () => {
  test('maps live and history to distinct server preference names', () => {
    expect(layoutViewName('live')).toBe('knowledge-live');
    expect(layoutViewName('history')).toBe('knowledge-history');
    expect(layoutRequestPath('task/a', 'knowledge-live'))
      .toBe('/api/v2/tasks/task%2Fa/layouts/knowledge-live');
  });

  test('parses a strict server preference and creates a patch without revision', () => {
    const value = parseLayoutPreference({
      schema_version: 'wuji.api.v2',
      view_name: 'knowledge-history',
      layout_revision: '17',
      selection_mode: 'explicit_revision',
      entries: layout.entries,
      viewport: layout.viewport,
    }, 'knowledge-history');
    const patch = layoutPatch(value);
    expect(patch).toEqual({
      schema_version: 'wuji.api.v2',
      selection_mode: 'explicit_revision',
      entries: layout.entries,
      viewport: layout.viewport,
    });
    expect('layout_revision' in patch).toBe(false);
    expect('view_name' in patch).toBe(false);
  });

  test('rejects extra fields, duplicate anchors, non-finite values, and wrong mode', () => {
    const base = {
      schema_version: 'wuji.api.v2',
      view_name: 'knowledge-live',
      layout_revision: '0',
      selection_mode: 'follow_latest',
      entries: [],
      viewport: { x: 0, y: 0, zoom: 0.82 },
    };
    expect(() => parseLayoutPreference({ ...base, internal_seq: 7 }, 'knowledge-live')).toThrow();
    expect(() => parseLayoutPreference({
      ...base,
      entries: [
        { anchor: { entity_type: 'origin', id: 't', revision: null }, x: 0, y: 0, pinned: false },
        { anchor: { entity_type: 'origin', id: 't', revision: null }, x: 1, y: 1, pinned: false },
      ],
    }, 'knowledge-live')).toThrow();
    expect(() => parseLayoutPreference({
      ...base,
      viewport: { x: Number.NaN, y: 0, zoom: 0.82 },
    }, 'knowledge-live')).toThrow();
    expect(() => parseLayoutPreference({
      ...base,
      selection_mode: 'explicit_revision',
    }, 'knowledge-live')).toThrow();
  });

  test('keeps HTTP status and server code for CAS conflicts', () => {
    const error = new LayoutRequestError(409, 'stale', 'STALE_VERSION');
    expect(error.status).toBe(409);
    expect(error.code).toBe('STALE_VERSION');
  });
});
