import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeftOutlined, SafetyCertificateOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Descriptions,
  Empty,
  Form,
  Input,
  InputNumber,
  Radio,
  Select,
  Spin,
} from 'antd';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ApiRequestError,
  StaleContextError,
  isApiError,
  type Project,
  type Session,
  type TaskDraft,
  type TaskPreview,
} from './api';
import { PrivatePage } from './pages';
import {
  leaveUnavailableProject,
  previewTask,
  projectQueryOptions,
  resetScopePages,
} from './queries';
import {
  EffectiveLimits,
  LimitsList,
  ScopeDetails,
  scopeBindingKey,
  scopeOptionLabel,
  useApprovedScopes,
} from './scopes';
import { useIdentitySnapshot } from './state';
import styles from './workbench.module.css';

interface TaskDraftForm {
  readonly name: string;
  readonly scopeKey?: string;
  readonly target_url: string;
  readonly method: 'GET' | 'HEAD';
  readonly limits: TaskDraft['limits'];
}

const initialDraft: TaskDraftForm = {
  name: '',
  target_url: '',
  method: 'GET',
  limits: {
    max_total_requests: 20,
    requests_per_second: 1,
    max_concurrent_requests: 1,
    request_timeout_seconds: 10,
    max_response_bytes: 1048576,
    max_runtime_seconds: 60,
  },
};

function finiteNumberRule(
  minimum: number,
  maximum: number,
  integer: boolean,
  exclusiveMinimum = false,
) {
  return {
    validator(_: unknown, value: unknown) {
      const valid = typeof value === 'number'
        && Number.isFinite(value)
        && (exclusiveMinimum ? value > minimum : value >= minimum)
        && value <= maximum
        && (!integer || Number.isInteger(value));
      return valid
        ? Promise.resolve()
        : Promise.reject(new Error(
          exclusiveMinimum
            ? `请输入大于 ${minimum} 且不超过 ${maximum} 的数字`
            : `请输入 ${minimum} 到 ${maximum} 之间的${integer ? '整数' : '数字'}`,
        ));
    },
  };
}

function PreviewError({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const apiError = error instanceof ApiRequestError ? error : null;
  let title = '任务预览失败';
  let body = '请求未完成，表单内容已保留。';
  if (apiError?.contractFailure) {
    title = '预览响应无法读取';
    body = '平台返回的数据格式无法识别。';
  } else if (apiError?.status === 403) {
    title = '任务预览权限已更新';
    body = '项目权限已重新读取，请确认当前身份后重试。';
  } else if (apiError?.status === 404) {
    title = '所选批准范围已不可用';
    body = apiError.message;
  } else if (apiError?.status === 422 || apiError?.status === 400) {
    title = '输入无法生成预览';
    body = apiError.message;
  } else if (apiError?.status === 0 || apiError?.status === 503) {
    title = '平台暂时不可用';
    body = '连接未完成，表单内容已保留。';
  }

  return (
    <Alert
      role="alert"
      type="error"
      showIcon
      title={title}
      description={(
        <div>
          <p>{body}</p>
          {apiError?.traceId && <code className={styles.trace}>追踪编号 {apiError.traceId}</code>}
        </div>
      )}
      action={<Button onClick={onRetry}>重试预览</Button>}
    />
  );
}

function TaskPreviewResult({ preview }: { preview: TaskPreview }) {
  const previewBlockers = preview.blockers.filter((blocker) => blocker.code !== 'CREATION_UNAVAILABLE');
  const creationBlocker = preview.blockers.find((blocker) => blocker.code === 'CREATION_UNAVAILABLE');
  const scopeReady = previewBlockers.length === 0;

  return (
    <section className={styles.previewResult} aria-labelledby="preview-result-title" data-testid="task-preview-result">
      <header className={styles.resultHeading}>
        <div>
          <span className={styles.eyebrow}>PREVIEW RESULT</span>
          <h2 id="preview-result-title">任务预览结果</h2>
        </div>
        <time dateTime={preview.expires_at}>
          有效至 {new Date(preview.expires_at).toLocaleString('zh-CN')}
        </time>
      </header>
      <div className={styles.previewStatus}>
        <Alert
          type={scopeReady ? 'success' : 'warning'}
          showIcon
          title={scopeReady ? '范围计算通过' : '预览存在阻断项'}
          description={scopeReady ? (
            '规范化后的目标与方法位于所选批准范围内。'
          ) : (
            <ul>
              {previewBlockers.map((blocker, index) => (
                <li key={`${blocker.code}:${index}`}>{blocker.message}</li>
              ))}
            </ul>
          )}
        />
        {creationBlocker && (
          <Alert
            type="info"
            showIcon
            title="任务创建尚未开放"
            description={creationBlocker.message}
          />
        )}
      </div>
      <div className={styles.resultSection}>
        <h3>规范化请求</h3>
        <Descriptions
          bordered
          size="small"
          column={{ xs: 1, sm: 1, md: 2 }}
          items={[
            { key: 'name', label: '任务名称', children: preview.draft.name },
            { key: 'method', label: '请求方法', children: preview.draft.method },
            {
              key: 'target',
              label: '规范化目标',
              span: 'filled',
              children: <code className={styles.breakCode}>{preview.draft.target_url}</code>,
            },
            {
              key: 'scope',
              label: '批准范围',
              span: 'filled',
              children: scopeOptionLabel(preview.effective_scope),
            },
          ]}
        />
      </div>
      <div className={styles.resultGrid}>
        <section className={styles.resultSection} aria-labelledby="effective-scope-title">
          <h3 id="effective-scope-title">有效范围</h3>
          <ScopeDetails scope={preview.effective_scope} />
        </section>
        <section className={styles.resultSection} aria-labelledby="requested-limits-title">
          <h3 id="requested-limits-title">规范化请求限额</h3>
          <LimitsList limits={preview.draft.limits} />
        </section>
        <section className={styles.resultSection} aria-labelledby="effective-limits-title">
          <h3 id="effective-limits-title">有效限额</h3>
          <EffectiveLimits scope={preview.effective_scope} />
        </section>
      </div>
    </section>
  );
}

function TaskPreviewWorkspace({
  session,
  project,
  refetchProject,
}: {
  session: Session;
  project: Project;
  refetchProject: () => Promise<{ error: Error | null }>;
}) {
  const navigate = useNavigate();
  const [form] = Form.useForm<TaskDraftForm>();
  const scopes = useApprovedScopes(session, project.id);
  const selectedScopeKey = Form.useWatch('scopeKey', form);
  const selectedScope = useMemo(
    () => scopes.items.find((scope) => scopeBindingKey(scope) === selectedScopeKey),
    [scopes.items, selectedScopeKey],
  );
  const revision = useRef(0);
  const activeRequest = useRef<AbortController | null>(null);
  const [preview, setPreview] = useState<TaskPreview | null>(null);
  const [previewError, setPreviewError] = useState<unknown>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => () => activeRequest.current?.abort(), []);

  const discardPreview = () => {
    revision.current += 1;
    activeRequest.current?.abort();
    activeRequest.current = null;
    setSubmitting(false);
    setPreview(null);
    setPreviewError(null);
  };

  const handleSubmit = async (values: TaskDraftForm) => {
    const scope = scopes.items.find((candidate) => scopeBindingKey(candidate) === values.scopeKey);
    if (!scope) {
      form.setFields([{ name: 'scopeKey', errors: ['请重新选择当前可用的批准范围'] }]);
      return;
    }

    const requestRevision = ++revision.current;
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setSubmitting(true);
    setPreview(null);
    setPreviewError(null);

    const draft: TaskDraft = {
      name: values.name,
      scope: scope.binding,
      target_url: values.target_url,
      tool: 'http_observe',
      method: values.method,
      limits: values.limits,
    };

    try {
      const result = await previewTask(session, project.id, draft, controller.signal);
      if (revision.current !== requestRevision || activeRequest.current !== controller) return;
      setPreview(result);
    } catch (error) {
      if (
        controller.signal.aborted
        || error instanceof StaleContextError
        || revision.current !== requestRevision
        || activeRequest.current !== controller
      ) {
        return;
      }

      if (isApiError(error, 403)) {
        setPreviewError(error);
        await refetchProject();
      } else if (isApiError(error, 404)) {
        const refreshed = await refetchProject();
        if (revision.current !== requestRevision || activeRequest.current !== controller) return;
        if (isApiError(refreshed.error, 404)) {
          leaveUnavailableProject(project.id);
          navigate('/projects?notice=project-unavailable', { replace: true });
          return;
        }
        if (refreshed.error) {
          setPreviewError(refreshed.error);
          return;
        }
        await resetScopePages(session, project.id);
        if (revision.current !== requestRevision || activeRequest.current !== controller) return;
        revision.current += 1;
        form.setFieldValue('scopeKey', undefined);
        activeRequest.current = null;
        setSubmitting(false);
        setPreviewError(new ApiRequestError({
          status: 404,
          code: 'NOT_FOUND',
          message: '所选范围已经失效或不再可见，请重新选择批准范围。',
          traceId: error.traceId,
        }));
      } else {
        setPreviewError(error);
      }
    } finally {
      if (revision.current === requestRevision && activeRequest.current === controller) {
        activeRequest.current = null;
        setSubmitting(false);
      }
    }
  };

  return (
    <section className={styles.taskPreviewPage} aria-labelledby="task-preview-title">
      <Link className={styles.backLink} to={`/projects/${project.id}`}>
        <ArrowLeftOutlined aria-hidden="true" />
        返回项目工作区
      </Link>
      <header className={styles.previewHeading}>
        <div>
          <span className={styles.eyebrow}>TASK PREVIEW</span>
          <h1 id="task-preview-title">任务预览</h1>
          <p>{project.name} · 预览不会访问目标。</p>
        </div>
        <SafetyCertificateOutlined aria-hidden="true" />
      </header>
      <div className={styles.previewLayout}>
        <section className={styles.previewFormPanel} aria-labelledby="task-draft-title">
          <header>
            <div>
              <h2 id="task-draft-title">任务草稿</h2>
              <p>选择批准范围，填写目标与请求限额。</p>
            </div>
          </header>
          <Form<TaskDraftForm>
            form={form}
            layout="vertical"
            initialValues={initialDraft}
            requiredMark="optional"
            onValuesChange={discardPreview}
            onFinish={(values) => void handleSubmit(values)}
          >
            <div className={styles.formGrid}>
              <Form.Item
                name="name"
                label="任务名称"
                rules={[
                  { required: true, whitespace: true, message: '请输入任务名称' },
                  { max: 120, message: '任务名称不能超过 120 个字符' },
                ]}
              >
                <Input maxLength={120} placeholder="用于识别本次观察" />
              </Form.Item>
              <Form.Item
                name="method"
                label="请求方法"
                rules={[{ required: true, message: '请选择请求方法' }]}
              >
                <Radio.Group optionType="button" buttonStyle="solid">
                  <Radio.Button value="GET">GET</Radio.Button>
                  <Radio.Button value="HEAD">HEAD</Radio.Button>
                </Radio.Group>
              </Form.Item>
              <Form.Item
                className={styles.fullField}
                name="target_url"
                label="目标 URL"
                rules={[
                  { required: true, message: '请输入绝对 HTTP(S) URL' },
                  { max: 2048, message: '目标 URL 不能超过 2048 个字符' },
                ]}
              >
                <Input maxLength={2048} placeholder="https://target.example/path" spellCheck={false} />
              </Form.Item>
              <Form.Item
                className={styles.fullField}
                name="scopeKey"
                label="批准范围"
                rules={[{ required: true, message: '请选择批准范围' }]}
              >
                <Select
                  loading={scopes.isPending}
                  disabled={scopes.isPending || scopes.items.length === 0}
                  placeholder="选择当前项目的批准范围"
                  options={scopes.items.map((scope) => ({
                    value: scopeBindingKey(scope),
                    label: scopeOptionLabel(scope),
                  }))}
                />
              </Form.Item>
            </div>

            {scopes.isPending ? (
              <div className={styles.formScopeStatus} role="status"><Spin description="正在读取批准范围" /></div>
            ) : scopes.items.length === 0 && !scopes.error ? (
              <div className={styles.formScopeStatus} role="status">
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无可用范围" />
              </div>
            ) : selectedScope ? (
              <div className={styles.selectedScope}>
                <h3>{selectedScope.label}</h3>
                <ScopeDetails scope={selectedScope} />
              </div>
            ) : null}

            {(scopes.hasNextPage || scopes.isFetchingNextPage) && (
              <Button
                className={styles.loadScopeButton}
                loading={scopes.isFetchingNextPage}
                onClick={() => void scopes.fetchNextPage()}
              >
                加载更多范围
              </Button>
            )}

            <fieldset className={styles.limitFields}>
              <legend>请求限额</legend>
              <Form.Item name={['limits', 'max_total_requests']} label="请求总数上限" rules={[finiteNumberRule(1, 200, true)]}>
                <InputNumber className={styles.numberInput} min={1} max={200} precision={0} />
              </Form.Item>
              <Form.Item name={['limits', 'requests_per_second']} label="每秒请求上限" rules={[finiteNumberRule(0, 2, false, true)]}>
                <InputNumber className={styles.numberInput} min={0} max={2} step={0.1} />
              </Form.Item>
              <Form.Item name={['limits', 'max_concurrent_requests']} label="并发请求上限" rules={[finiteNumberRule(1, 2, true)]}>
                <InputNumber className={styles.numberInput} min={1} max={2} precision={0} />
              </Form.Item>
              <Form.Item name={['limits', 'request_timeout_seconds']} label="单次超时（秒）" rules={[finiteNumberRule(1, 10, true)]}>
                <InputNumber className={styles.numberInput} min={1} max={10} precision={0} />
              </Form.Item>
              <Form.Item name={['limits', 'max_response_bytes']} label="响应大小上限（字节）" rules={[finiteNumberRule(1, 1048576, true)]}>
                <InputNumber className={styles.numberInput} min={1} max={1048576} precision={0} />
              </Form.Item>
              <Form.Item name={['limits', 'max_runtime_seconds']} label="总运行时限（秒）" rules={[finiteNumberRule(1, 600, true)]}>
                <InputNumber className={styles.numberInput} min={1} max={600} precision={0} />
              </Form.Item>
            </fieldset>

            {scopes.error && !isApiError(scopes.error, 404) && !isApiError(scopes.error, 410) && (
              <Alert
                className={styles.formAlert}
                role="alert"
                type="error"
                showIcon
                title="批准范围读取失败"
                description="请求未完成，请重试读取范围。"
                action={<Button onClick={() => void scopes.refetch()}>重试读取范围</Button>}
              />
            )}
            {previewError !== null && <PreviewError error={previewError} onRetry={() => form.submit()} />}
            <div className={styles.formActions}>
              <Button
                type="primary"
                htmlType="submit"
                loading={submitting}
                disabled={scopes.isPending || scopes.items.length === 0}
              >
                生成任务预览
              </Button>
            </div>
          </Form>
        </section>
        <aside className={styles.previewAside} aria-label="预览说明">
          <h2>操作提示</h2>
          <ol>
            <li>选择当前项目的批准范围。</li>
            <li>填写目标、方法与请求限额。</li>
            <li>生成预览并核对有效范围与限额。</li>
          </ol>
        </aside>
      </div>
      {preview && <TaskPreviewResult preview={preview} />}
    </section>
  );
}

function TaskPreviewContent({ session, projectId }: { session: Session; projectId: string }) {
  const identity = useIdentitySnapshot();
  const navigate = useNavigate();
  const project = useQuery(projectQueryOptions(session, projectId));

  useEffect(() => {
    if (isApiError(project.error, 404)) {
      leaveUnavailableProject(projectId);
      navigate('/projects?notice=project-unavailable', { replace: true });
    }
  }, [navigate, project.error, projectId]);

  if (project.isPending) {
    return <div className={styles.centerStatus} role="status"><Spin description="正在读取项目" /></div>;
  }
  if (!project.data) {
    return (
      <Alert
        role="alert"
        type="error"
        showIcon
        title="项目读取失败"
        description="请求未完成，请重试。"
        action={<Button onClick={() => void project.refetch()}>重试</Button>}
      />
    );
  }
  if (!project.data.permissions.includes('project.read')) {
    return <Alert role="alert" type="error" showIcon title="当前项目无可用权限" />;
  }
  if (!project.data.permissions.includes('task.preview')) {
    return (
      <section className={styles.routeError}>
        <Alert
          role="alert"
          type="warning"
          showIcon
          title="当前身份只能查看批准范围"
          description="请返回项目工作区查看范围；此身份不能提交任务预览。"
        />
        <Button onClick={() => navigate(`/projects/${projectId}`)}>返回项目工作区</Button>
      </section>
    );
  }

  return (
    <TaskPreviewWorkspace
      key={`${identity.identityGeneration}:${identity.projectGeneration}:${projectId}`}
      session={session}
      project={project.data}
      refetchProject={project.refetch}
    />
  );
}

export function TaskPreviewPage() {
  const { projectId = '' } = useParams();
  return (
    <PrivatePage>
      {(session) => <TaskPreviewContent session={session} projectId={projectId} />}
    </PrivatePage>
  );
}
