import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Empty, Spin, Tag, Typography } from 'antd';
import { ApiRequestError } from '../../api';
import { readExploration, type ExplorationViewV1 } from '../../v2WorkbenchApi';
import type { KnowledgeRef } from '../topology/contracts';
import styles from './problemBoard.module.css';

interface ProblemBoardProps {
  readonly taskId: string;
  readonly mode: 'live' | 'history';
  readonly snapshotId: string | null;
  readonly refreshKey: number;
  readonly onSnapshotChange: (snapshotId: string) => void;
  readonly onSelect: (ref: KnowledgeRef) => void;
  readonly onSessionExpired: () => void;
}

function refLabel(ref: KnowledgeRef): string {
  return `${ref.entity_type}:${ref.id}@${ref.revision}`;
}

export function ProblemBoard({ taskId, mode, snapshotId, refreshKey, onSnapshotChange, onSelect, onSessionExpired }: ProblemBoardProps) {
  const [view, setView] = useState<ExplorationViewV1 | null>(null);
  const [error, setError] = useState<string | null>(null);
  const generation = useRef(0);

  useEffect(() => {
    const current = generation.current + 1;
    generation.current = current;
    const controller = new AbortController();
    setView(null);
    setError(null);
    void readExploration(taskId, mode, snapshotId, controller.signal).then((next) => {
      if (controller.signal.aborted || generation.current !== current) return;
      setView(next);
      onSnapshotChange(next.snapshot_id);
    }).catch((reason: unknown) => {
      if (controller.signal.aborted || generation.current !== current) return;
      if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      setError(reason instanceof Error ? reason.message : '问题黑板读取失败');
    });
    return () => controller.abort();
  }, [taskId, mode, snapshotId, refreshKey, onSnapshotChange, onSessionExpired]);

  if (error) return <Alert showIcon type="warning" title="问题黑板读取受限" description={error} />;
  if (!view) return <div aria-live="polite"><Spin description="正在读取问题、认识和依据" /></div>;
  if (view.problems.length === 0 && view.insights.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="尚无问题或认识记录；不会生成虚构历史" />;
  }

  return (
    <div className={styles.board} data-testid="problem-board">
      <div className={styles.summary}>
        <Tag color="blue">问题 {view.problems.length}</Tag>
        <Tag color="cyan">认识 {view.insights.length}</Tag>
        <Tag>进行中 {view.execution_summary.active_work}</Tag>
        <Tag color={view.execution_summary.needs_attention ? 'orange' : 'default'}>需处理 {view.execution_summary.needs_attention}</Tag>
        <Typography.Text type="secondary">固定快照 {view.snapshot_id}</Typography.Text>
      </div>
      <div className={styles.grid}>
        <section className={styles.column} aria-label="问题列表">
          <h3>当前问题</h3>
          {view.problems.map((problem) => (
            <article className={styles.card} key={refLabel(problem.intent_ref)}>
              <Button type="link" className={styles.title} onClick={() => onSelect(problem.intent_ref)}>{problem.question}</Button>
              <dl>
                <div><dt>为什么做</dt><dd>{problem.public_rationale ?? '未记录'}</dd></div>
                <div><dt>执行状态</dt><dd>{problem.execution_state ?? '待关联'}</dd></div>
                <div><dt>得到了什么</dt><dd>{problem.work_result?.summary ?? '尚未生成结果'}</dd></div>
                <div><dt>还缺什么</dt><dd>{problem.gaps.length ? problem.gaps.join('；') : '未记录缺口'}</dd></div>
              </dl>
              <div className={styles.refs}>
                <span>依据</span>
                {problem.basis_refs.length === 0 ? <em>未记录</em> : problem.basis_refs.map((ref) => <Button type="link" size="small" key={refLabel(ref)} onClick={() => onSelect(ref)}>{refLabel(ref)}</Button>)}
              </div>
              <div className={styles.attempts}>
                <span>已尝试</span>
                {problem.attempts.length === 0 ? <em>未记录</em> : problem.attempts.map((attempt) => <Tag key={attempt.source_ref}>{attempt.summary}</Tag>)}
              </div>
            </article>
          ))}
        </section>
        <section className={styles.column} aria-label="认识列表">
          <h3>已有认识</h3>
          {view.insights.map((insight) => (
            <article className={styles.card} key={refLabel(insight.claim_ref)}>
              <Button type="link" className={styles.title} onClick={() => onSelect(insight.claim_ref)}>{insight.text}</Button>
              <div className={styles.summary}><Tag>{insight.kind}</Tag><Tag>{insight.evidence_state}</Tag><Tag>{insight.applicability_state}</Tag></div>
              {insight.limitations.length > 0 && <p>限制：{insight.limitations.join('；')}</p>}
              <div className={styles.refs}>
                <span>来源</span>
                {insight.source_refs.length === 0 ? <em>未记录</em> : insight.source_refs.map((ref) => <Button type="link" size="small" key={refLabel(ref)} onClick={() => onSelect(ref)}>{refLabel(ref)}</Button>)}
              </div>
            </article>
          ))}
        </section>
      </div>
      {view.relations.length > 0 && <section className={styles.relations} aria-label="问题关系"><h3>关系</h3>{view.relations.map((relation) => <code key={relation.relation_id}>{relation.source_ref} —{relation.kind}→ {relation.target_ref}</code>)}</section>}
      {view.missing_fields.length > 0 && <Typography.Text type="secondary">旧记录未提供：{view.missing_fields.join('、')}。页面不会补造。</Typography.Text>}
    </div>
  );
}
