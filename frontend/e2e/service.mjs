import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { mkdirSync, rmSync, createWriteStream } from 'node:fs';
import { resolve } from 'node:path';

const kind = process.argv[2];
// A synthetic CDR data holder for live product checks (public PRD endpoints).
const holderProduct = (id, name, extra = {}) => ({
  productId: id, lastUpdated: '2026-01-15T00:00:00Z', productCategory: 'PERS_LOANS', name,
  description: `${name} for e2e checks.`, brand: 'FIXTURE', isTailored: false, ...extra,
});
const holderRate = rate => ({
  lendingRateType: 'VARIABLE', rate, comparisonRate: '0.0899', applicationType: 'PERIODIC',
  applicationFrequency: 'P1M', repaymentType: 'PRINCIPAL_AND_INTEREST', loanPurpose: 'OTHER',
});
const holderDetails = {
  'FIX-1': holderProduct('FIX-1', 'Fixture Personal Loan', { lendingRates: [holderRate('0.0849')] }),
  'FIX-2': holderProduct('FIX-2', 'Fixture Percent Loan', { lendingRates: [holderRate('8.49')] }),
};
function serveHolder(req, res) {
  if (!req.headers['x-v']) { res.writeHead(400); res.end('{}'); return; }
  const list = req.url === '/holder/cds-au/v1/banking/products?page-size=100';
  const detail = holderDetails[req.url.split('/banking/products/')[1]];
  res.setHeader('x-v', list ? '5' : '7');
  if (list) {
    res.end(JSON.stringify({ data: { products: Object.values(holderDetails).map(({ lendingRates, ...summary }) => summary) }, links: {}, meta: { totalRecords: 2, totalPages: 1 } }));
  } else if (detail) {
    res.end(JSON.stringify({ data: detail, links: {} }));
  } else {
    res.writeHead(404); res.end('{}');
  }
}
mkdirSync('e2e-logs', { recursive: true });
const log = createWriteStream(`e2e-logs/${kind}.log`, { flags: 'w' });
if (kind === 'model') {
  let mode = 'normal', calls = 0;
  createServer(async (req, res) => {
    let raw = ''; for await (const chunk of req) raw += chunk;
    res.setHeader('Content-Type', 'application/json');
    if (req.url.startsWith('/holder/')) { serveHolder(req, res); return; }
    if (req.url === '/reset' && req.method === 'POST') {
      mode = JSON.parse(raw).mode ?? 'normal'; calls = 0;
    } else if (req.url === '/v1/chat/completions' && req.method === 'POST') {
      calls++;
      // Never log request headers, credentials, or sample values.
      log.write(`completion ${calls}: ${mode}\n`);
      const payload = JSON.parse(raw);
      if (payload.model !== 'fixture-model' || !Array.isArray(payload.messages)) {
        res.writeHead(400); res.end('{}'); return;
      }
      if (mode === '503') { res.writeHead(503); res.end('{}'); return; }
      const isPhone = payload.messages[0]?.content?.includes('phone-number normalization rule assistant');
      const content = isPhone && mode === 'normal' ? JSON.stringify({ transformation_type: 'phone_normalization', default_region: 'AU', target_format: 'E164', preserve_invalid: true, explanation: 'Synthetic phone rule' }) : mode === 'invalid-json' ? 'not json' : JSON.stringify({
        regex: mode === 'invalid-regex' ? '[' : 'TOKEN-[0-9]+', flags: [],
        explanation: 'Synthetic marker rule', confidence: 'high',
      });
      res.end(JSON.stringify({ choices: [{ message: { content } }] })); return;
    } else if (req.url !== '/state') { res.writeHead(404); }
    res.end(JSON.stringify({ mode, calls }));
  }).listen(8766, '127.0.0.1');
} else {
  const python = process.env.E2E_PYTHON || 'python';
  const env = { ...process.env, DJANGO_SETTINGS_MODULE: 'config.test_settings', PYTHONUNBUFFERED: '1', VITE_API_BASE_URL: 'http://127.0.0.1:8765/api' };
  let child;
  const run = (command, args, cwd) => new Promise((done) => {
    child = spawn(command, args, { cwd, env, stdio: ['ignore', 'pipe', 'pipe'] });
    child.stdout.pipe(log, { end: false }); child.stderr.pipe(log, { end: false });
    child.on('error', error => { log.write(error.message); done(1); });
    child.on('exit', code => done(code ?? 1));
  });
  for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => { child?.kill(signal); });
  let code;
  if (kind === 'backend') {
    const runtime = resolve('../.e2e-runtime');
    rmSync(runtime, { recursive: true, force: true }); mkdirSync(runtime, { recursive: true });
    code = await run(python, ['manage.py', 'migrate', '--noinput'], '../backend');
    if (!code) code = await run(python, ['manage.py', 'runserver', '127.0.0.1:8765', '--noreload'], '../backend');
  } else {
    code = await run('npm', ['run', 'build'], '.');
    if (!code) code = await run('npm', ['run', 'preview', '--', '--host', '127.0.0.1', '--port', '4173', '--strictPort'], '.');
  }
  process.exitCode = code;
}
