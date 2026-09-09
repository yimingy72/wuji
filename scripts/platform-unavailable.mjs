const command = process.argv[2] ?? 'platform lifecycle';

console.error(`${command} is not available in the Phase 1A CORE batch; SERVER must implement and verify this lifecycle.`);
process.exitCode = 1;
