"""One P04 review counterexample; production code is imported without modification."""
from pathlib import Path
import base64
import gzip
import hashlib
import json
import sys

ROOT = Path('/Users/yym1ng/Documents/ChatGPT/wuji/work/worktrees/vnext-maf')
OUT = Path(__file__).parent / 'evidence'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'tests/vnext'))
from support.postgres import isolated_database_environment
from test_knowledge_admission import case, proposal, post_claim, assess, get_claim, captured, access, TASK

with isolated_database_environment(
    manifest_path=ROOT / 'work/vnext/postgres-fixture.json',
    audit_path=OUT / 'postgres-events.jsonl',
) as env:
    with case(env, OUT, OUT) as c:
        with env.migration_connection() as m:
            m.execute("UPDATE vnext.task_access SET clearance=0 WHERE task_id=%s AND subject='reader-fixture'", (TASK,))
        premise = post_claim(c, proposal('Public premise v1', kind='observation-summary')).json()['canonical_ref']
        derived = post_claim(c, proposal('Conclusion supported by the premise', kind='derived-conclusion', basis=[premise])).json()['canonical_ref']
        checked = assess(c, derived, [premise], kind='human_attestation', method='human-attestation-v1', role='human')
        assert checked.status_code == 202, checked.text
        before = get_claim(c, derived, role='reader')
        assert before.status_code == 200 and before.json()['assessment']['eligible'] is True
        private, private_obs = captured(c, body=b'{"updated_premise":false}', access_level=1)
        revised = post_claim(c, proposal('Revised private premise v2', kind='observation-summary', basis=[private_obs], revises=premise))
        assert revised.status_code == 202, revised.text
        assert revised.json()['canonical_ref']['revision'] == '2'
        high = get_claim(c, derived, role='agent')
        low = get_claim(c, derived, role='reader')
        with c.uow.transaction(access('agent-fixture', role='agent'), TASK) as tx:
            identity = tx.connection.execute("SELECT current_user,rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user").fetchone()
            revisions = tx.connection.execute('SELECT entity_id,revision,access_level FROM vnext.claim_revision WHERE entity_id=%s ORDER BY revision', (premise['id'],)).fetchall()
        observed = {
            'head': '18d03323e9da1d23cca33b4dcc82bee170e7eee8',
            'scenario': 'Public assessment input v1 has an actual private v2; lower-clearance latest-version query misses v2',
            'premise_ref': premise,
            'derived_ref': derived,
            'new_revision_ref': revised.json()['canonical_ref'],
            'application_role': identity,
            'actual_premise_revisions': [[i, str(v), level] for i,v,level in revisions],
            'before': {'status': before.status_code, 'body': before.json()},
            'high': {'status': high.status_code, 'body': high.json()},
            'low': {'status': low.status_code, 'body': low.json()},
        }
        observed['counterexample_reproduced'] = high.status_code == low.status_code == 200 and high.json()['assessment']['eligible'] is False and low.json()['assessment']['eligible'] is True
        (OUT / 'observed.json').write_text(json.dumps(observed, ensure_ascii=False, indent=2) + '\n')

# Retain full requests/responses; replace only ephemeral fixture bearer credentials.
http = OUT / 'http-exchanges.jsonl'
sanitized = []
for line in http.read_text().splitlines():
    e = json.loads(line)
    auth = e['request']['headers'].get('authorization')
    if auth:
        claims = json.loads(base64.urlsafe_b64decode(auth.removeprefix('Bearer ').split('.')[1] + '==='))
        e['request']['headers']['authorization'] = 'Bearer ${TOKEN_' + claims['sub'].replace('-', '_') + '}'
        e['authorization_evidence'] = {'subject': claims['sub'], 'roles': claims['roles'], 'original_header_sha256': hashlib.sha256(auth.encode()).hexdigest(), 'replacement': 'regenerate ephemeral fixture token using test issuer'}
    sanitized.append(e)
http.write_text(''.join(json.dumps(e, ensure_ascii=False, sort_keys=True) + '\n' for e in sanitized))
parts = ['# P04 review counterexample — complete ASGI HTTP exchanges\n',
         'Production routes and isolated PostgreSQL; not an external target. Only fixture Authorization credentials are redacted. Re-run counterexample.py with the existing isolated test database manifest; it creates and cleans up only its own temporary database/roles. Full SQL and sealed input bytes accompany this file.\n',
         'Failure point: after private premise revision 2, the final low-clearance GET still returns supported/current/eligible=true while the preceding high-clearance GET returns unassessed/stale/eligible=false.\n']
for n,e in enumerate(sanitized, 1):
    parts.append(f'## Exchange {n}\n')
    for side in ['request', 'response']:
        d = e[side]
        prefix = d['method'] + ' ' + d['url'] + ' HTTP/1.1' if side == 'request' else 'HTTP/1.1 ' + str(d['status_code'])
        parts.append('```http\n' + prefix + '\n' + '\n'.join(k + ': ' + v for k,v in d['headers'].items()) + '\n\n' + base64.b64decode(d['body_base64']).decode() + '\n```\n')
(OUT / 'http-reproduction.md').write_text('\n'.join(parts))
sql = OUT / 'postgres-events.jsonl'
(OUT / 'postgres-events.jsonl.gz').write_bytes(gzip.compress(sql.read_bytes(), mtime=0))
print(json.dumps({'counterexample_reproduced': observed['counterexample_reproduced'], 'high': observed['high']['body']['assessment'], 'low': observed['low']['body']['assessment'], 'actual_premise_revisions': observed['actual_premise_revisions'], 'application_role': identity, 'evidence': str(OUT)}, ensure_ascii=False, indent=2))
assert observed['counterexample_reproduced'], 'Named risk was not reproduced; do not claim a confirmed finding.'
