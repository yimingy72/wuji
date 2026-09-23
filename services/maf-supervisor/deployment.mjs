// Fixed deployment files only; no fixture bootstrap or authority fabrication.
import { readFileSync, statSync } from 'node:fs';
import { isAbsolute } from 'node:path';
import { ControllerAdapter, mafProfile } from './controller-adapter.mjs';
import { parseJson } from './protocol.mjs';

function read(path, maximum = 1048576) {
  if (!isAbsolute(path) || statSync(path).size > maximum) throw new Error('invalid deployment file');
  return readFileSync(path);
}

export async function buildSupervisor() {
  const config = parseJson(read(process.env.WUJI_DEPLOYMENT_CONFIG ?? '/config/supervisor.json').toString());
  const expected = ['schema_version','controller_origin','receiver','receiver_token_file',
    'profiles','inbox_dir','ca_file','certificate_file','private_key_file','port'];
  const core = config.template_version === 'core-ctf-v1';
  const fields = core ? [...expected,'template_version','namespace'] : expected;
  if (Object.keys(config).length !== fields.length || fields.some(k => !Object.hasOwn(config, k))
      || config.schema_version !== 'wuji.supervisor.deployment.v1'
      || !Number.isInteger(config.port) || config.port < 1 || config.port > 65535
      || (core && (typeof config.namespace !== 'string'
        || !/^[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?$/.test(config.namespace)))
      || process.env.NODE_EXTRA_CA_CERTS !== config.ca_file) throw new Error('invalid Supervisor deployment');
  if (Object.hasOwn(config.receiver, 'pod_uid') || !process.env.WUJI_POD_UID
      || process.env.WUJI_POD_NAMESPACE !== (core ? config.namespace : 'wuji-vnext-test')) throw new Error('Downward API Pod identity required');
  const receiver = {...config.receiver, pod_uid:process.env.WUJI_POD_UID};
  const adapter = new ControllerAdapter({origin:config.controller_origin, receiver,
    authorization:() => read(config.receiver_token_file,16384).toString().trim()});
  const profiles = Object.fromEntries(Object.entries(config.profiles).map(([ref, workKinds]) => [ref,
    mafProfile({pythonExecutable:'/opt/wuji/packages/maf-worker/.venv/bin/python',cwd:'/opt/wuji',
      env:{PATH:'/opt/wuji/packages/maf-worker/.venv/bin:/usr/local/bin:/usr/bin:/bin',
        PYTHONDONTWRITEBYTECODE:'1',WUJI_TLS_CA_FILE:config.ca_file},workKinds})]));
  return {inboxDir:config.inbox_dir,receiver,profiles,
    authorize:adapter.authorize,bootstrap:adapter.bootstrap,persistResults:adapter.persistResults,
    authenticate:adapter.authenticate,host:'0.0.0.0',port:config.port,
    tls:{cert:read(config.certificate_file),key:read(config.private_key_file)},
    maxBodyBytes:1048576};
}
