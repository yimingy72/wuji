import { fileURLToPath } from 'node:url';

const webModules = fileURLToPath(new URL('../../../apps/web/node_modules/', import.meta.url));

export default {
  resolve: {
    alias: [
      { find: /^react$/, replacement: `${webModules}react` },
      { find: /^react\/(.*)$/, replacement: `${webModules}react/$1` },
      { find: /^react-dom$/, replacement: `${webModules}react-dom` },
      { find: /^react-dom\/(.*)$/, replacement: `${webModules}react-dom/$1` },
      { find: /^react-router-dom$/, replacement: `${webModules}react-router-dom` },
    ],
  },
};
