import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Empty, Segmented, Spin, Tag } from 'antd';
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

function findingState(insight: ExplorationViewV1['insights'][number]): { readonly label: string; readonly color: string } {
  if (insight.evidence_state === 'supported' && insight.applicability_state === 'current') return { label: '已确认', color: 'green' };
  if (insight.evidence_state === 'contradicted') return { label: '有反证', color: 'red' };
  return { label: '待验证', color: 'gold' };
}

export function ProblemBoard({ taskId, mode, snapshotId, refreshKey, onSnapshotChange, onSelect, onSessionExpired }: ProblemBoardProps) {
  const [view, setView] = useState<ExplorationViewV1 | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [section, setSection] = useState<'problems' | 'findings'>('problems');
  const [selected, setSelected] = useState<string | null>(null);
  const generation = useRef(0);

  useEffect(() => {
    const current = generation.current + 1;
    generation.current = current;
    const controller = new AbortController();
    setView(null);
    setError(null);
    setSelected(null);
    void readExploration(taskId, mode, snapshotId, controller.signal).then((next) => {
      if (controller.signal.aborted || generation.current !== current) return;
      setView(next);
      onSnapshotChange(next.snapshot_id);
    }).catch((reason: unknown) => {
      if (controller.signal.aborted || generation.current !== current) return;
      if (reason instanceof ApiRequestError && reason.status === 401) onSessionExpired();
      setError(reason instanceof Error ? reason.message : '发现与证据读取失败');
    });
    return () => controller.abort();
  }, [taskId, mode, snapshotId, refreshKey, onSnapshotChange, onSessionExpired]);

  if (error) return <Alert showIcon type="warning" title="发现与证据读取失败" description={error} />;
  if (!view) return <div aria-live="polite"><Spin description="正在读取问题与发现" /></div>;
  if (view.problems.length === 0 && view.insights.length === 0) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前还没有问题或发现" />;
  }

  const selectedProblem = view.problems.find((item) => refLabel(item.intent_ref) === selected) ?? null;
  const selectedFinding = view.insights.find((item) => refLabel(item.claim_ref) === selected) ?? null;
  const selectedRef = selectedProblem ? refLabel(selectedProblem.intent_ref) : selectedFinding ? refLabel(selectedFinding.claim_ref) : null;
  const localRelations = selectedRef
    ? view.relations.filter((item) => item.source_ref === selectedRef || item.target_ref === selectedRef)
    : [];
  const confirmed = view.insights.filter((item) => findingState(item).label === '已确认').length;
  const contradicted = view.insights.filter((item) => findingState(item).label === '有反证').length;

  return (
    <div className={styles.board} data-testid="problem-board">
      <div className={styles.toolbar}>
        <Segmented
          value={section}
          options={[
            { value: 'problems', label: `问题 ${view.problems.length}` },
            { value: 'findings', label: `发现 ${view.insights.length}` },
          ]}
          onChange={(value) => { setSection(value as 'problems' | 'findings'); setSelected(null); }}
        />
        <div className={styles.summary}>
          <Tag color="green">已确认 {confirmed}</Tag>
          <Tag color="red">有反证 {contradicted}</Tag>
          <Tag color={view.execution_summary.needs_attention ? 'orange' : 'default'}>需处理 {view.execution_summary.needs_attention}</Tag>
        </div>
      </div>
      <div className={styles.masterDetail}>
        <section className={styles.list} aria-label={section === 'problems' ? '问题列表' : '发现列表'}>
          {section === 'problems' && view.problems.map((problem) => {
            const key = refLabel(problem.intent_ref);
            return <button type="button" className={`${styles.listItem} ${selected === key ? styles.selected : ''}`} key={key} onClick={() => { setSelected(key); onSelect(problem.intent_ref); }}>
              <span className={styles.itemHeading}><strong>{problem.question}</strong><Tag>{problem.execution_state ?? '待处理'}</Tag></span>
              <span className={styles.clamp}>{problem.work_result?.summary ?? problem.public_rationale ?? '尚无结果摘要'}</span>
              {problem.gaps.length > 0 && <small>{problem.gaps.length} 个未解项</small>}
            </button>;
          })}
          {section === 'findings' && view.insights.map((insight) => {
            const key = refLabel(insight.claim_ref);
            const state = findingState(insight);
            return <button type="button" className={`${styles.listItem} ${selected === key ? styles.selected : ''}`} key={key} onClick={() => { setSelected(key); onSelect(insight.claim_ref); }}>
              <span className={styles.itemHeading}><strong>{insight.text}</strong><Tag color={state.color}>{state.label}</Tag></span>
              <span className={styles.clamp}>{insight.limitations[0] ?? `${insight.kind} · ${insight.evidence_state}`}</span>
              <small>支持 {insight.supporting_refs.length} · 反对 {insight.opposing_refs.length}</small>
            </button>;
          })}
        </section>
        <section className={styles.detail} aria-label="所选条目详情">
          {!selectedProblem && !selectedFinding && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="选择一项查看依据和执行详情" />}
          {selectedProblem && <>
            <header><Tag>{selectedProblem.execution_state ?? '待处理'}</Tag><h3>{selectedProblem.question}</h3></header>
            {selectedProblem.public_rationale && <p>{selectedProblem.public_rationale}</p>}
            <dl>
              <div><dt>当前结果</dt><dd>{selectedProblem.work_result?.summary ?? '尚无结果'}</dd></div>
              <div><dt>未解项</dt><dd>{selectedProblem.gaps.length ? selectedProblem.gaps.join('；') : '无'}</dd></div>
            </dl>
            <div className={styles.refs}><span>依据</span>{selectedProblem.basis_refs.length ? selectedProblem.basis_refs.map((ref) => <Button type="link" size="small" key={refLabel(ref)} onClick={() => onSelect(ref)}>{ref.entity_type} · {ref.id}</Button>) : <em>暂无</em>}</div>
            <details><summary>执行步骤（{selectedProblem.attempts.length}）</summary>{selectedProblem.attempts.length ? <ul className={styles.steps}>{selectedProblem.attempts.map((attempt) => <li key={attempt.source_ref}><Tag>{attempt.status}</Tag><span>{attempt.summary}</span></li>)}</ul> : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无执行步骤" />}</details>
          </>}
          {selectedFinding && <>
            <header><Tag color={findingState(selectedFinding).color}>{findingState(selectedFinding).label}</Tag><h3>{selectedFinding.text}</h3></header>
            <dl><div><dt>证据状态</dt><dd>{selectedFinding.evidence_state}</dd></div><div><dt>适用状态</dt><dd>{selectedFinding.applicability_state}</dd></div></dl>
            {selectedFinding.limitations.length > 0 && <p>限制：{selectedFinding.limitations.join('；')}</p>}
            <div className={styles.refs}><span>支持依据</span>{selectedFinding.supporting_refs.length ? selectedFinding.supporting_refs.map((ref) => <Button type="link" size="small" key={refLabel(ref)} onClick={() => onSelect(ref)}>{ref.entity_type} · {ref.id}</Button>) : <em>暂无</em>}</div>
            <div className={styles.refs}><span>反对依据</span>{selectedFinding.opposing_refs.length ? selectedFinding.opposing_refs.map((ref) => <Button type="link" size="small" key={refLabel(ref)} onClick={() => onSelect(ref)}>{ref.entity_type} · {ref.id}</Button>) : <em>暂无</em>}</div>
          </>}
          {localRelations.length > 0 && <details><summary>查看局部关联（{localRelations.length}）</summary><div className={styles.relations}>{localRelations.map((relation) => <code key={relation.relation_id}>{relation.source_ref} —{relation.kind}→ {relation.target_ref}</code>)}</div></details>}
        </section>
      </div>
      <details className={styles.dataDetails}><summary>数据说明</summary><code>snapshot {view.snapshot_id}</code>{view.missing_fields.length > 0 && <p>旧记录未提供：{view.missing_fields.join('、')}</p>}</details>
    </div>
  );
}
