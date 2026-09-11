import type { WebDraftContentV2 } from '../../api';
export function AuthorizationSummary({authorization}: {authorization: WebDraftContentV2['authorization']}) {
  if (!authorization) return <p>未填写授权范围</p>;
  return <div><h3>本任务授权</h3><ul>{(authorization.includes ?? []).map((r, i) => <li key={i}>{r.host}{r.include_subdomains ? '（包含子域）' : ''} · {r.endpoint.scheme}:{r.endpoint.port}</li>)}</ul><h4>排除</h4>{(authorization.excludes ?? []).length ? <ul>{(authorization.excludes ?? []).map((r, i) => <li key={i}>{r.host}{r.include_subdomains ? '（包含子域）' : ''} · {r.endpoints === 'all_included' ? '全部包含协议端口' : r.endpoints.map(e => `${e.scheme}:${e.port}`).join('、')}</li>)}</ul> : <p>无排除项</p>}<p>授权截止：{authorization.valid_until ? new Date(authorization.valid_until).toLocaleString('zh-CN') : '未填写'}</p></div>;
}
