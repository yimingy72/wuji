#!/usr/bin/env python3
"""Validate this documentation package, never the Wuji implementation.

No network, model, database, shell subprocess, or framework runtime is invoked.
The embedded product test snippets are parsed only, not executed.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import re
import sys
from datetime import datetime
from importlib.metadata import version
from pathlib import Path
from urllib.parse import unquote

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError as exc:
    raise SystemExit('Missing jsonschema. Install checks/requirements.txt first.') from exc

ROOT = Path(__file__).resolve().parents[1]

def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result

def reject_constant(value):
    raise ValueError(f'non-finite JSON number: {value}')

def load(path: str):
    return json.loads((ROOT / path).read_text(encoding='utf-8'),
                      object_pairs_hook=no_duplicates, parse_constant=reject_constant)

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(condition, detail):
    if not condition:
        raise AssertionError(detail)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify-manifest', action='store_true')
    parser.add_argument('--no-write-report', action='store_true')
    args = parser.parse_args()
    results=[]
    def check(name, fn):
        try:
            detail=fn()
            results.append({'name':name,'status':'pass','detail':str(detail)})
        except Exception as exc:
            results.append({'name':name,'status':'fail','detail':f'{type(exc).__name__}: {exc}'})
    req=load('requirements.json'); tasks=load('plan_tasks.json'); acs=load('acceptance_cases.json')
    findings=load('audit_findings.json'); contracts=load('contracts.json'); trace=load('traceability.json')
    rids={x['id'] for x in req}; tids={x['id'] for x in tasks}; aids={x['id'] for x in acs}; fids={x['id'] for x in findings}
    spec=(ROOT/'SPEC.md').read_text(); plan=(ROOT/'PLAN.md').read_text(); review=(ROOT/'REVIEW.md').read_text(); acc=(ROOT/'ACCEPTANCE.md').read_text()
    def all_json():
        paths=list(ROOT.rglob('*.json'))
        for p in paths:load(p.relative_to(ROOT).as_posix())
        return f'{len(paths)} JSON files parsed with duplicate-key/nonfinite rejection'
    check('JSON文件可解析',all_json)
    def identity():
        for values,ids,prefix in [(req,rids,'REQ'),(tasks,tids,'P'),(acs,aids,'AC'),(findings,fids,'REV')]:
            require(len(values)==len(ids),f'{prefix} duplicate IDs')
        require(rids=={f'REQ-{i:03}' for i in range(1,41)},'REQ IDs')
        require(tids=={f'P{i:02}' for i in range(21)},'task IDs')
        require(aids=={f'AC-{i:03}' for i in range(1,76)},'AC IDs')
        require(fids=={f'REV-{i:02}' for i in range(1,35)},'review IDs')
        return '40 requirements / 21 tasks / 75 acceptance cases / 34 findings'
    check('编号唯一且连续',identity)
    def references():
        sections=set(re.findall(r'<a id="(S\d+)"',spec))
        for q in req:
            require(set(q['sections'])<=sections,q['id']+' bad section')
            require(set(q['tasks'])<=tids,q['id']+' bad task')
            require(q['id'] in spec,q['id']+' absent in SPEC')
        for a in acs:
            require(set(a['requirements'])<=rids,a['id']+' bad REQ')
            require(set(a['tasks'])<=tids,a['id']+' bad task')
            require(a['status']=='not_run',a['id']+' product status inflated')
            require(a['id'] in acc,a['id']+' absent in ACCEPTANCE')
            for k in ['setup','action','expected','negative_control']:require(bool(a[k].strip()),a['id']+k)
        for f in findings:
            require(set(f['sections'])<=sections,f['id']+' section')
            require(set(f['tasks'])<=tids,f['id']+' task')
            require(set(f['tests'])<=aids,f['id']+' tests')
            require(f['id'] in review,f['id']+' absent in REVIEW')
        require({q for a in acs for q in a['requirements']}==rids,'uncovered requirements')
        require({t for a in acs for t in a['tasks']}==tids,'task without case')
        return 'All indexed references resolve; all planned product cases remain not_run'
    check('需求与验收交叉引用',references)
    def task_dag():
        done=set()
        for p in tasks:
            require(set(p['depends_on'])<=done,p['id']+' not ordered / circular dependency')
            require(set(p['acceptance'])<=aids,p['id']+' AC')
            expected={a['id'] for a in acs if p['id'] in a['tasks']}
            require(set(p['acceptance'])==expected,p['id']+' AC mismatch')
            require(p['code'].rstrip() in plan,p['id']+' representative test mismatch')
            if p['testpath']:require(p['testpath'] in p['files'],p['id']+' test path omitted')
            done.add(p['id'])
        return 'P00–P20 ordered dependency graph is acyclic; tests match plan text'
    check('计划依赖与正文一致',task_dag)
    def trace_refs():
        require({t['requirement_id'] for t in trace}==rids,'trace REQ')
        for t in trace:
            require(set(t['acceptance_cases'])=={a['id'] for a in acs if t['requirement_id'] in a['requirements']},t['requirement_id']+' trace AC')
            require(set(t['implementation_tasks'])<=tids,t['requirement_id']+' trace task')
            require(set(t['review_findings'])<=fids,t['requirement_id']+' trace REV')
            require(t['runtime_status']=='not_run','trace runtime status')
        return f'{len(trace)} bidirectional requirement entries consistent'
    check('追溯矩阵一致',trace_refs)
    def source_integrity():
        source=load('source_manifest.json')
        for entry in source:
            p=ROOT/entry['path']
            require(p.stat().st_size==entry['bytes'],str(p)+' size')
            require(sha(p)==entry['sha256'],str(p)+' SHA-256')
            require(len(p.read_text().splitlines())==entry['lines'],str(p)+' lines')
        for f in findings:
            lines=(ROOT/'source'/f['source_file']).read_text().splitlines()
            require(all(1<=n<=len(lines) for n in f['lines']),f['id']+' source line range')
            # An excerpt is required to match an actually quoted line, not a guessed location.
            require(any(f['source_excerpt']==lines[n-1] for n in f['lines']),f['id']+' source excerpt mismatch')
        return f'{len(source)} archived originals unchanged; 34 excerpts match recorded lines'
    check('原件摘要与复审定位',source_integrity)
    def shape_and_state():
        enum=contracts['enums']; states=set(enum['work_state'])
        require('superseded' not in states,'undefined WorkItem state')
        for a,b in contracts['work_transitions']:
            require(a in states and b in states,f'unknown transition {a}->{b}')
            require(a not in {'done','failed','cancelled'},'terminal state has outgoing transition')
        require('incomplete' in enum['report_delivery'],'missing delivery incomplete')
        require(set(enum['component_receipt_status'])=={'accepted_shared','accepted_for_check','rejected'},'component receipt ambiguity')
        schema=load('checks/example.schema.json');Draft202012Validator.check_schema(schema)
        for name,fields in contracts['wire_required_fields'].items():
            if name in schema['$defs']:
                require(set(fields)==set(schema['$defs'][name]['required']),name+' required mismatch')
        return 'State endpoints valid; terminal states remain terminal; required fields match example-profile schema'
    check('状态与示例合同一致',shape_and_state)
    def example_validation():
        schema=load('checks/example.schema.json');idx=load('examples/index.json')
        good=bad=0
        for e in idx:
            candidate={**schema,'$ref':'#/$defs/'+e['schema_definition']}
            errors=list(Draft202012Validator(candidate,format_checker=FormatChecker()).iter_errors(load(e['path'])))
            require((not errors)==e['expected_valid'],e['path']+' '+('; '.join(x.message for x in errors[:2]) or 'unexpectedly accepted'))
            if e['expected_valid']:good+=1
            else:bad+=1
        s=load('examples/topology_snapshot.json');b=load('examples/view_event_batch.json')
        require(int(b['view_revision'])==int(b['base_view_revision'])+1,'view numerical order')
        require(s['view_id']==b['view_id'],'view binding')
        require(b['base_view_revision']==s['view_revision'],'snapshot/batch watermarks')
        for n in s['nodes']:
            q=n['ref'];require(n['id']==f"{q['entity_type']}:{q['id']}@{q['revision']}",'node id')
        require(all(k not in b for k in ['board_revision','task_event_seq']),'external seq leakage')
        return f'{good} positive examples accepted / {bad} explicit negative examples rejected; basic identity/watermark invariants checked'
    check('示例正反例与基本不变量',example_validation)
    def snippets():
        total=0;ts=0
        for p in [ROOT/'SPEC.md',ROOT/'PLAN.md',ROOT/'ACCEPTANCE.md']:
            text=p.read_text();require(len(re.findall(r'^```',text,re.M))%2==0,p.name+' unbalanced code fence')
            for lang,code in re.findall(r'^```([^\n]*)\n(.*?)^```',text,re.M|re.S):
                if lang.strip()=='python': ast.parse(code);total+=1
                if lang.strip() in ('typescript','tsx','ts'):ts+=1
        return f'{total} Python blocks AST-parsed only; {ts} TypeScript blocks not compiled or executed'
    check('代码片段静态语法与围栏',snippets)
    def links():
        count=0
        for p in list(ROOT.glob('*.md'))+list((ROOT/'examples').glob('*.md')):
            text=p.read_text()
            # Archived source links are intentionally historical and excluded.
            for target in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)',text):
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target):continue
                path,sep,anchor=target.partition('#')
                q=(p.parent/unquote(path)).resolve() if path else p
                require(q.is_file(),f'{p.name} missing link: {target}')
                if anchor and re.match(r'^(S\d+|P\d+|REV-\d+)$',anchor):
                    require(f'id="{anchor}"' in q.read_text(),target+' missing anchor')
                count+=1
            require(not re.search(r'\b(?:TODO|TBD)\b|PLACEHOLDER',text),p.name+' unresolved placeholder')
        return f'{count} current-document local file/explicit-anchor links resolve; no unresolved placeholder markers; external and archived URLs not revalidated'
    check('当前文档本地链接与占位符',links)
    def manifest_check():
        entries=load('artifact_manifest.json');require(bool(entries),'empty manifest')
        expected={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and p.name!='artifact_manifest.json' and '__pycache__' not in p.parts}
        actual={e['path'] for e in entries};require(expected==actual,'manifest path set differs')
        for e in entries:require(sha(ROOT/e['path'])==e['sha256'],e['path']+' changed')
        return f'{len(entries)} packaged files SHA-256 verified; manifest excludes itself'
    if args.verify_manifest:check('交付文件清单摘要',manifest_check)
    failures=[x for x in results if x['status']=='fail']
    for x in results: print(f"[{x['status'].upper()}] {x['name']}: {x['detail']}")
    print(f'Document checks: {len(results)-len(failures)}/{len(results)} passed. Product tests: NOT RUN.')
    if not args.no_write_report:
        timestamp=datetime.now().astimezone().isoformat(timespec='seconds')
        rows='\n'.join('| '+x['name']+' | '+x['status']+' | '+x['detail'].replace('|',' / ')+' |' for x in results)
        report=f'''# 文档验证报告\n\n**文档日期：2026-09-13；版本：2.0-review。**\n\n以下记录由实际运行 `python checks/validate_documents.py` 生成；容器记录时间为 `{timestamp}`（可能与对话所设日期/时区不同，未据此改写源文档日期）。\n\n- Python：`{sys.version.split()[0]}`\n- jsonschema：`{version('jsonschema')}`\n- 本轮检查结果：**{len(results)-len(failures)}/{len(results)} 项通过**。\n- 产品验收状态：**75 条均为 not_run**。\n\n| 检查 | 结果 | 实际覆盖 |\n|---|---|---|\n{rows}\n\n## 校验器修正记录\n\n打包复核曾发现生成报告中的检查说明包含被扫描的占位标记词，导致报告扫描自身时误报。已改写该说明并重新执行全套文档检查，未关闭该项检查。\n\n## 这份结果不证明什么\n\n没有安装/执行 MAF Agent、模型网关或真实模型；没有运行 PostgreSQL/RLS/并发测试；没有启动 Supervisor/Kubernetes/外部工具；没有编译 React Flow/TypeScript 或跑浏览器；没有验证 Mermaid 布局；没有运行 Plan 的产品pytest/Vitest/Playwright。Python块只AST解析，导入与测试逻辑未执行。JSON示例schema只覆盖明示示例profile，并非已完成OpenAPI。\n\n需求映射和数量只能证明索引有对应项，不能证明架构正确、完全无遗漏或CTF/靶场效果。34项复审发现是人工文档推理结果，不是34个已复现产品故障。source摘要证明原件未修改，不证明原件里每个陈述真实。\n\n最终打包后另运行 `python checks/validate_documents.py --verify-manifest --no-write-report`，防止改写本报告而循环改变清单；该命令退出码在交付时检查。本轮没有改用户仓库或提交实现代码。\n'''
        (ROOT/'VALIDATION_REPORT.md').write_text(report)
    return 1 if failures else 0

if __name__=='__main__':
    raise SystemExit(main())
