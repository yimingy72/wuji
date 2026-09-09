import { useEffect, useMemo, useRef } from 'react';
import { Alert, Button, Empty, Spin, Tag } from 'antd';
import { useInfiniteQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  ApiRequestError,
  isApiError,
  type ApprovedScope,
  type Limits,
  type Session,
} from './api';
import {
  leaveUnavailableProject,
  refreshSession,
  resetScopePages,
  scopePagesQueryOptions,
} from './queries';
import styles from './workbench.module.css';

const limitLabels = {
  max_total_requests: '请求总数',
  requests_per_second: '每秒请求数',
  max_concurrent_requests: '并发请求数',
  request_timeout_seconds: '单次超时（秒）',
  max_response_bytes: '响应上限（字节）',
  max_runtime_seconds: '运行时限（秒）',
} as const;

export function scopeBindingKey(scope: ApprovedScope): string {
  return `${scope.binding.policy_id}:${scope.binding.version}`;
}

export function scopeOptionLabel(scope: ApprovedScope): string {
  return `${scope.label} · 版本 ${scope.binding.version}`;
}

export function useApprovedScopes(session: Session, projectId: string) {
  const navigate = useNavigate();
  const handledError = useRef<unknown>(null);
  const query = useInfiniteQuery(scopePagesQueryOptions(session, projectId));
  const items = useMemo(
    () => query.data?.pages.flatMap((page) => page.items) ?? [],
    [query.data?.pages],
  );

  useEffect(() => {
    if (!query.error) {
      handledError.current = null;
      return;
    }
    if (handledError.current === query.error) return;
    handledError.current = query.error;

    if (isApiError(query.error, 404)) {
      leaveUnavailableProject(projectId);
      navigate('/projects?notice=project-unavailable', { replace: true });
      return;
    }
    if (isApiError(query.error, 410)) {
      void refreshSession().catch(() => undefined);
      void resetScopePages(session, projectId);
    }
  }, [navigate, projectId, query.error, session]);

  return { ...query, items };
}

function ScopeError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const apiError = error instanceof ApiRequestError ? error : null;
  return (
    <Alert
      role="alert"
      type="error"
      showIcon
      title="批准范围读取失败"
      description={apiError?.contractFailure ? '平台返回的数据格式无法识别。' : '请求未完成，请重试。'}
      action={<Button onClick={onRetry}>重试读取范围</Button>}
    />
  );
}

export function ScopeDetails({ scope }: { scope: ApprovedScope }) {
  return (
    <div className={styles.scopeDetails}>
      <div>
        <span>允许来源</span>
        <div className={styles.valueList}>
          {scope.origins.map((origin, index) => <code key={`${origin}:${index}`}>{origin}</code>)}
        </div>
      </div>
      <div>
        <span>允许路径</span>
        <div className={styles.valueList}>
          {scope.allowed_path_prefixes.map((path, index) => <code key={`${path}:${index}`}>{path}</code>)}
        </div>
      </div>
      <div>
        <span>排除路径</span>
        <div className={styles.valueList}>
          {scope.excluded_path_prefixes.length > 0
            ? scope.excluded_path_prefixes.map((path, index) => <code key={`${path}:${index}`}>{path}</code>)
            : <span>无</span>}
        </div>
      </div>
      <div>
        <span>允许方法</span>
        <div className={styles.methodList}>
          {scope.allowed_methods.map((method, index) => <Tag key={`${method}:${index}`}>{method}</Tag>)}
        </div>
      </div>
      <div>
        <span>授权有效期</span>
        <time dateTime={scope.valid_until}>{new Date(scope.valid_until).toLocaleString('zh-CN')}</time>
      </div>
    </div>
  );
}

export function LimitsList({ limits }: { limits: Limits }) {
  return (
    <dl className={styles.limitList}>
      {Object.entries(limitLabels).map(([key, label]) => (
        <div key={key}>
          <dt>{label}</dt>
          <dd>{limits[key as keyof Limits]}</dd>
        </div>
      ))}
    </dl>
  );
}

export function EffectiveLimits({ scope }: { scope: ApprovedScope }) {
  return <LimitsList limits={scope.limits} />;
}

export function ApprovedScopesPanel({ session, projectId }: { session: Session; projectId: string }) {
  const scopes = useApprovedScopes(session, projectId);
  const retry = scopes.isFetchNextPageError
    ? () => { void scopes.fetchNextPage(); }
    : () => { void scopes.refetch(); };

  return (
    <section className={styles.scopePanel} aria-labelledby="approved-scopes-title">
      <header>
        <div>
          <h2 id="approved-scopes-title">批准范围</h2>
          <p>当前项目可用于非破坏性 HTTP 观察的范围。</p>
        </div>
        <span>{scopes.items.length} 项</span>
      </header>
      {scopes.isPending ? (
        <div className={styles.scopeStatus} role="status"><Spin description="正在读取批准范围" /></div>
      ) : scopes.error && !isApiError(scopes.error, 410) && !isApiError(scopes.error, 404) ? (
        <div className={styles.scopeStatus}><ScopeError error={scopes.error} onRetry={retry} /></div>
      ) : scopes.items.length === 0 ? (
        <div className={styles.scopeStatus} role="status">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可用范围" />
        </div>
      ) : (
        <div className={styles.scopeList} role="list" aria-label="批准范围列表">
          {scopes.items.map((scope) => (
            <article className={styles.scopeItem} role="listitem" key={scopeBindingKey(scope)}>
              <div className={styles.scopeItemHeading}>
                <div>
                  <h3>{scope.label}</h3>
                  <span>版本 {scope.binding.version}</span>
                </div>
                <Tag color="success">已批准</Tag>
              </div>
              <ScopeDetails scope={scope} />
              <div className={styles.scopeLimits}>
                <h4>范围限额</h4>
                <LimitsList limits={scope.limits} />
              </div>
            </article>
          ))}
        </div>
      )}
      {(scopes.hasNextPage || scopes.isFetchingNextPage) && (
        <footer className={styles.scopePagination}>
          <span>范围按批准时间排序</span>
          <Button loading={scopes.isFetchingNextPage} onClick={() => void scopes.fetchNextPage()}>
            加载更多范围
          </Button>
        </footer>
      )}
    </section>
  );
}
