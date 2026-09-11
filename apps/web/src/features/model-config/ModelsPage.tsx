import { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Alert, Button, Form, Input, Select } from 'antd';
import { Link, useParams } from 'react-router-dom';
import { actOnModel, ApiRequestError, findModelOperation, getModelDefinitions, getModelVersions, getTenants, readModelOperation, saveModelVersion, type ModelKind, type ModelOperation, type ModelVersion, type ProfileVersionRequest, type ServiceVersionRequest, type Session } from '../../api';
import { identityRequest } from '../../queries';
import { PrivatePage } from '../../pages';
import styles from '../../workbench.module.css';

const stateLabel = {draft: '草稿', published: '已发布', retired: '已停用', revoked: '已撤销'};
const syncLabel = {pending: '同步中', synced: '已同步', failed: '同步失败', unknown: '同步待核对'};
const opLabel = {prepared: '已记录', sent: '已发送', succeeded: '已完成', failed: '失败', unknown: '结果待核对'};
const required = [{required: true, message: '请填写此项'}];
const amount = [{required: true, pattern: /^(0|[1-9][0-9]{0,11})(\.[0-9]{1,12})?$/, message: '请输入有效 USD 单价'}];

export function TenantModelsLinks({session}: {session: Session}) {
  const [cursor, setCursor] = useState<string | null>(null);
  const tenants = useQuery({queryKey: ['private', 'tenants', session.user_id, session.permissions_version, cursor], queryFn: ({signal}) => identityRequest(session, () => getTenants(cursor, signal))});
  return <div className={styles.inlineActions}>{tenants.data?.items.filter(t => t.permissions.includes('model.config.read')).map(t => <Link key={t.id} to={`/settings/tenants/${t.id}/models`}>{t.name} · 模型设置</Link>)}{tenants.data?.next_cursor && <Button onClick={() => setCursor(tenants.data!.next_cursor)}>更多组织</Button>}</div>;
}

interface ModelForm {
  name: string; protocol: 'openai' | 'anthropic'; base_url: string; api_key: string;
  service_version_id: string; model_id: string; context_window?: string; max_output_tokens?: string;
  timeout_seconds: string; price_mode: 'missing' | 'configured'; source: string;
  input_per_million: string; output_per_million: string; cache_mode?: 'standard_input' | 'separate';
  cache_read_per_million: string; cache_creation_per_million: string;
}

function ModelsContent({session, tenantId}: {session: Session; tenantId: string}) {
  const [kind, setKind] = useState<ModelKind>('service');
  const [definitionId, setDefinitionId] = useState<string | null>(null);
  const [cursor, setCursor] = useState<string | null>(null);
  const [versionCursor, setVersionCursor] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [serviceDefinition, setServiceDefinition] = useState<string | null>(null);
  const [serviceCursor, setServiceCursor] = useState<string | null>(null);
  const [serviceVersionCursor, setServiceVersionCursor] = useState<string | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [operation, setOperation] = useState<ModelOperation | null>(null);
  const storageKey = `wuji.model-operation.v1.${session.user_id}.${tenantId}`;
  const [pendingKey, setPendingKey] = useState<string | null>(() => {try {return sessionStorage.getItem(storageKey);} catch {return null;}});
  const [form] = Form.useForm<ModelForm>();
  const priceMode = Form.useWatch('price_mode', form);
  const cacheMode = Form.useWatch('cache_mode', form);
  const abort = useRef(new AbortController());
  useEffect(() => {const current = new AbortController(); abort.current = current; return () => {current.abort(); form.resetFields();};}, [form]);
  const definitions = useQuery({queryKey: ['private', 'models', session.user_id, session.permissions_version, tenantId, kind, cursor], queryFn: ({signal}) => identityRequest(session, () => getModelDefinitions(tenantId, kind, cursor, signal))});
  const versions = useQuery({queryKey: ['private', 'model-versions', session.user_id, session.permissions_version, tenantId, kind, definitionId, versionCursor], enabled: Boolean(definitionId), queryFn: ({signal}) => identityRequest(session, () => getModelVersions(tenantId, kind, definitionId!, versionCursor, signal))});
  const serviceDefinitions = useQuery({queryKey: ['private', 'model-service-choices', session.user_id, session.permissions_version, tenantId, serviceCursor], enabled: editing && kind === 'profile', queryFn: ({signal}) => identityRequest(session, () => getModelDefinitions(tenantId, 'service', serviceCursor, signal))});
  const serviceVersions = useQuery({queryKey: ['private', 'model-service-version-choices', session.user_id, session.permissions_version, tenantId, serviceDefinition, serviceVersionCursor], enabled: editing && kind === 'profile' && Boolean(serviceDefinition), queryFn: ({signal}) => identityRequest(session, () => getModelVersions(tenantId, 'service', serviceDefinition!, serviceVersionCursor, signal))});
  const refresh = () => {void definitions.refetch(); if (definitionId) void versions.refetch();};
  const accept = (op: ModelOperation) => {
    setOperation(op);
    if (op.state === 'succeeded' || op.state === 'failed') {sessionStorage.removeItem(storageKey); setPendingKey(null);}
    refresh();
  };
  const perform = async (request: (key: string, signal: AbortSignal) => Promise<ModelOperation>) => {
    if (pendingKey || busy) return;
    setError('');
    const key = crypto.randomUUID();
    try {sessionStorage.setItem(storageKey, key);} catch {setError('无法保存操作核对标记，请恢复浏览器存储后重试。'); return;}
    setPendingKey(key); setOperation(null); setBusy(true);
    try {accept(await identityRequest(session, () => request(key, abort.current.signal))); setEditing(false); form.resetFields();}
    catch (e) {
      if (abort.current.signal.aborted) return;
      if (e instanceof ApiRequestError && !e.contractFailure && e.status >= 400 && e.status < 500) {sessionStorage.removeItem(storageKey); setPendingKey(null);}
      setError(e instanceof ApiRequestError ? e.message : '响应不明，请核对原操作。');
      form.setFieldValue('api_key', '');
    } finally {if (!abort.current.signal.aborted) setBusy(false);}
  };
  const reconcile = async () => {
    if (!pendingKey) return;
    setBusy(true); setError('');
    try {accept(await identityRequest(session, () => operation ? readModelOperation(tenantId, operation.id, abort.current.signal) : findModelOperation(tenantId, pendingKey, abort.current.signal)));}
    catch (e) {if (!abort.current.signal.aborted) setError(e instanceof ApiRequestError && e.status === 404 ? '暂未查到原操作，保留标识，稍后继续核对。' : '核对未完成，请重试。');}
    finally {if (!abort.current.signal.aborted) setBusy(false);}
  };
  const edit = (version?: ModelVersion) => {
    form.resetFields();
    if (version) {
      const config = version.config;
      form.setFieldsValue({name: version.name, ...('protocol' in config ? {protocol: config.protocol, base_url: config.base_url} : {
        service_version_id: config.service_version_id, model_id: config.model_id,
        context_window: config.context_window?.toString(), max_output_tokens: config.max_output_tokens?.toString(), timeout_seconds: config.timeout_seconds.toString(),
        price_mode: config.pricing ? 'configured' : 'missing', ...(config.pricing ?? {}), cache_read_per_million: config.pricing?.cache_read_per_million ?? '', cache_creation_per_million: config.pricing?.cache_creation_per_million ?? '',
      }), api_key: ''});
    }
    setEditing(true);
  };
  const save = (v: ModelForm) => {
    if (kind === 'service') {
      const body: ServiceVersionRequest = {name: v.name, config: {protocol: v.protocol, base_url: v.base_url}, api_key: v.api_key};
      void perform((key, signal) => saveModelVersion(tenantId, kind, definitionId, body, session.csrf_token, key, signal));
    } else {
      if (v.price_mode === 'configured' && !v.cache_mode) {setError('请选择缓存计价方式。'); return;}
      const body: ProfileVersionRequest = {name: v.name, config: {service_version_id: v.service_version_id, model_id: v.model_id,
        context_window: v.context_window ? Number(v.context_window) : null, max_output_tokens: v.max_output_tokens ? Number(v.max_output_tokens) : null,
        timeout_seconds: Number(v.timeout_seconds), pricing: v.price_mode === 'missing' ? null : {
          source: v.source, input_per_million: v.input_per_million, output_per_million: v.output_per_million, cache_mode: v.cache_mode!,
          cache_read_per_million: v.cache_mode === 'separate' ? v.cache_read_per_million : null, cache_creation_per_million: v.cache_mode === 'separate' ? v.cache_creation_per_million : null,
        }}};
      void perform((key, signal) => saveModelVersion(tenantId, kind, definitionId, body, session.csrf_token, key, signal));
    }
  };
  return <section className={styles.projectPage}>
    <Link to="/projects">返回项目</Link>
    <header className={styles.pageHeading}><h1>组织模型设置</h1><Select aria-label="配置类型" value={kind} options={[{value: 'service', label: '模型服务'}, {value: 'profile', label: '模型方案'}]} onChange={value => {setKind(value); setDefinitionId(null); setCursor(null); setVersionCursor(null); setEditing(false); form.resetFields();}} /></header>
    {error && <Alert type="error" showIcon title={error} />}
    {pendingKey && <Alert type="warning" showIcon title="操作待核对" description="保留原标识；核对不会重新保存或发起模型检查。" action={<Button loading={busy} onClick={() => void reconcile()}>核对原操作</Button>} />}
    {operation && <Alert type={operation.state === 'failed' ? 'error' : 'info'} title={`${opLabel[operation.state]}${operation.result.error_code ? ` · ${operation.result.error_code}` : ''}`} />}
    {definitions.error ? <Alert type="error" title="当前组织模型配置不可访问" description="需要此组织的模型管理权限。" /> : <>
      <div className={styles.inlineActions}><Select aria-label={kind === 'service' ? '模型服务' : '模型方案'} placeholder="选择已有配置" value={definitionId} options={definitions.data?.items.map(d => ({value: d.id, label: d.name}))} onChange={id => {setDefinitionId(id); setVersionCursor(null); setEditing(false);}} style={{minWidth: 260}} />
        <Button disabled={busy || Boolean(pendingKey)} onClick={() => {setDefinitionId(null); edit();}}>新建{kind === 'service' ? '服务' : '方案'}</Button>
        {definitions.data?.next_cursor && <Button onClick={() => setCursor(definitions.data!.next_cursor)}>下一页配置</Button>}{cursor && <Button onClick={() => setCursor(null)}>返回首批</Button>}
      </div>
      {versions.error && <Alert type="error" title="版本读取失败" action={<Button onClick={() => void versions.refetch()}>重试</Button>} />}
      {versions.data?.items.map(version => <article className={styles.workspacePanel} key={version.id} style={{display: 'block', padding: 20, marginTop: 12}}>
        <h2>{version.name} · V{version.number}</h2><p>{stateLabel[version.state]} · {syncLabel[version.sync_state]}</p><code>{version.id}</code>
        {'protocol' in version.config ? <p>{version.config.protocol} · {version.config.base_url}</p> : <><p>{version.config.model_id} · 上下文 {version.config.context_window ?? '未填写'} · 最大输出 {version.config.max_output_tokens ?? '未填写'} · 超时 {version.config.timeout_seconds} 秒</p><p>{version.config.pricing ? `公司价格：输入 ${version.config.pricing.input_per_million} / 输出 ${version.config.pricing.output_per_million} USD / 百万 token · ${version.config.pricing.source}` : '未填写价格，不能发布'}</p></>}
        <div className={styles.inlineActions}><Button disabled={busy || Boolean(pendingKey)} onClick={() => edit(version)}>保存新版本</Button>{kind === 'profile' && (['check', 'publish', 'retire', 'revoke'] as const).map(action => <Button key={action} danger={action === 'revoke'} disabled={busy || Boolean(pendingKey) || (action === 'publish' && ('protocol' in version.config || !version.config.pricing))} onClick={() => void perform((key, signal) => actOnModel(tenantId, version, action, session.csrf_token, key, signal))}>{{check: '检查连接', publish: '发布', retire: '停用', revoke: '安全撤销'}[action]}</Button>)}</div>
        {version.state === 'revoked' && <p>平台已撤销；网关阻断：{syncLabel[version.sync_state]}。</p>}
      </article>)}
      {versions.data?.next_cursor && <Button onClick={() => setVersionCursor(versions.data!.next_cursor)}>下一页版本</Button>}{versionCursor && <Button onClick={() => setVersionCursor(null)}>返回最新版本</Button>}
      {editing && <Form<ModelForm> form={form} layout="vertical" autoComplete="off" initialValues={{protocol: 'openai', timeout_seconds: '30', price_mode: 'missing'}} onFinish={save} style={{maxWidth: 720, marginTop: 24}}>
        <h2>{definitionId ? '保存新版本' : '新建配置'}</h2><Form.Item name="name" label="名称" rules={required}><Input maxLength={120} /></Form.Item>
        {kind === 'service' ? <><Form.Item name="protocol" label="协议" rules={required}><Select options={[{value: 'openai', label: 'OpenAI 兼容'}, {value: 'anthropic', label: 'Anthropic'}]} /></Form.Item><Form.Item name="base_url" label="服务地址" rules={required}><Input /></Form.Item><Form.Item name="api_key" label="API Key（每个新版本重新填写）" rules={required}><Input.Password autoComplete="new-password" /></Form.Item></> : <>
          <Form.Item label="模型服务"><Select aria-label="选择模型服务" value={serviceDefinition} options={serviceDefinitions.data?.items.map(d => ({value: d.id, label: d.name}))} onChange={id => {setServiceDefinition(id); setServiceVersionCursor(null);}} /></Form.Item>{serviceDefinitions.data?.next_cursor && <Button onClick={() => setServiceCursor(serviceDefinitions.data!.next_cursor)}>下一页服务</Button>}{serviceCursor && <Button onClick={() => setServiceCursor(null)}>返回首批服务</Button>}<Form.Item name="service_version_id" label="服务版本" rules={required}><Select placeholder="先选择模型服务" options={serviceVersions.data?.items.map(v => ({value: v.id, label: `${v.name} · V${v.number} · ${syncLabel[v.sync_state]}`, disabled: v.sync_state !== 'synced'}))} /></Form.Item>{serviceVersions.data?.next_cursor && <Button onClick={() => setServiceVersionCursor(serviceVersions.data!.next_cursor)}>下一页服务版本</Button>}<Form.Item name="model_id" label="模型标识" rules={required}><Input /></Form.Item>
          <Form.Item name="context_window" label="上下文容量"><Input type="number" min={1} /></Form.Item><Form.Item name="max_output_tokens" label="最大输出 token"><Input type="number" min={1} /></Form.Item><Form.Item name="timeout_seconds" label="请求超时（秒）" rules={required}><Input type="number" min={1} max={60} /></Form.Item>
          <Form.Item name="price_mode" label="公司价格"><Select options={[{value: 'missing', label: '暂不填写（保存和检查，不可发布）'}, {value: 'configured', label: '填写公司网关价格'}]} /></Form.Item>
          {priceMode === 'configured' && <><Form.Item name="source" label="价格来源" rules={required}><Input /></Form.Item><Form.Item name="input_per_million" label="输入 USD / 百万 token" rules={amount}><Input /></Form.Item><Form.Item name="output_per_million" label="输出 USD / 百万 token" rules={amount}><Input /></Form.Item><Form.Item name="cache_mode" label="缓存计价" rules={required}><Select options={[{value: 'standard_input', label: '按普通输入价'}, {value: 'separate', label: '分别定价'}]} /></Form.Item>{cacheMode === 'separate' && <><Form.Item name="cache_read_per_million" label="缓存读取 USD / 百万 token" rules={amount}><Input /></Form.Item><Form.Item name="cache_creation_per_million" label="缓存写入 USD / 百万 token" rules={amount}><Input /></Form.Item></>}</>}
        </>}
        <div className={styles.inlineActions}><Button type="primary" htmlType="submit" loading={busy} disabled={Boolean(pendingKey)}>保存</Button><Button onClick={() => {form.resetFields(); setEditing(false);}}>关闭</Button></div>
      </Form>}
    </>}
  </section>;
}

export function ModelsPage() {
  const {tenantId = ''} = useParams();
  return <PrivatePage>{session => <ModelsContent key={`${session.user_id}:${session.permissions_version}:${tenantId}`} session={session} tenantId={tenantId} />}</PrivatePage>;
}
