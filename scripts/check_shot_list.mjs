// Run from the repository root after building apps/web. Browser requests use controlled fixtures.
import http from 'node:http'
import fs from 'node:fs/promises'
import path from 'node:path'
import { spawn } from 'node:child_process'
import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
const repo = process.cwd()
const temp = await fs.mkdtemp('/tmp/animation-jobs-')
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
let chrome, ws
const server = http.createServer(async (req, res) => {
  try {
    const file = path.join(repo, 'apps/web/dist', req.url === '/' ? 'index.html' : req.url)
    res.setHeader(
      'Content-Type',
      {
        '.html': 'text/html',
        '.js': 'text/javascript',
        '.css': 'text/css',
        '.svg': 'image/svg+xml',
      }[path.extname(file)] || 'application/octet-stream',
    )
    res.end(await fs.readFile(file))
  } catch {
    res.writeHead(404).end()
  }
})
async function launch(binary, args, expression, options = {}) {
  const child = spawn(binary, args, { stdio: ['ignore', 'ignore', 'pipe'], ...options })
  try {
    const address = await new Promise((resolve, reject) => {
      let log = ''
      const timer = setTimeout(() => reject(new Error('Process startup timeout')), 15000)
      child.on('error', reject)
      child.once('exit', (code) => {
        clearTimeout(timer)
        reject(new Error(`Process exited ${code}: ${log}`))
      })
      child.stderr.on('data', (chunk) => {
        log += chunk
        const match = log.match(expression)
        if (match) {
          clearTimeout(timer)
          resolve(match[1])
        }
      })
    })
    return [child, address]
  } catch (error) {
    child.kill()
    throw error
  }
}
const fixture = JSON.parse(
  execFileSync(
    '.venv/bin/python',
    [
      '-c',
      "from animation_studio.providers.planner import MockPlanner, PlannerRequest; print(MockPlanner().plan(PlannerRequest(prompt='নদীর ধারে')).model_dump_json())",
    ],
    { encoding: 'utf8' },
  ),
)
try {
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
  let endpoint
  ;[chrome, endpoint] = await launch(
    process.env.CHROME_BIN || '/opt/google/chrome/chrome',
    [
      '--headless=new',
      '--no-sandbox',
      '--disable-gpu',
      '--disable-dev-shm-usage',
      '--no-first-run',
      '--remote-debugging-port=0',
      `--user-data-dir=${temp}/chrome`,
      'about:blank',
    ],
    /DevTools listening on (ws:\/\/\S+)/,
  )
  ws = new WebSocket(endpoint)
  await new Promise((resolve) => ws.addEventListener('open', resolve, { once: true }))
  let id = 0,
    sessionId
  const pending = new Map()
  function send(method, params = {}) {
    return new Promise((resolve, reject) => {
      const next = ++id
      pending.set(next, { resolve, reject })
      ws.send(JSON.stringify({ id: next, method, params, ...(sessionId ? { sessionId } : {}) }))
    })
  }
  ws.addEventListener('message', (event) => {
    const message = JSON.parse(event.data)
    if (message.id) {
      const item = pending.get(message.id)
      pending.delete(message.id)
      if (message.error) item.reject(new Error(JSON.stringify(message.error)))
      else item.resolve(message.result)
    }
  })
  const target = await send('Target.createTarget', { url: 'about:blank' })
  sessionId = (await send('Target.attachToTarget', { targetId: target.targetId, flatten: true }))
    .sessionId
  await send('Runtime.enable')
  await send('Page.enable')
  await send('Page.addScriptToEvaluateOnNewDocument', {
    source: `
    window.previewMode='hold'; window.previewFixture=${JSON.stringify(fixture)};
    window.previewCalls=0; window.renderCalls=0; window.savedPlan={plan:window.previewFixture,revision:0,approved:false,result:null};
    const originalFetch=window.fetch.bind(window);
    window.fetch=async (url, options={}) => {
      if(!String(url).startsWith('http://127.0.0.1:8000')) return originalFetch(url,options);
      if(String(url).endsWith('/mock-render')) window.renderCalls++;
      const response=(value,status=200)=>new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
      if(String(url).includes('/plan') && options.method) {
        if(window.failSave) return response({detail:'Save failed'},503);
        const body=JSON.parse(options.body);
        if(options.method==='PUT') window.savedPlan={plan:body.plan,revision:window.savedPlan.revision+1,approved:false,result:null};
        else if(String(url).endsWith('/approve')) window.savedPlan.approved=true;
        else window.savedPlan.result=window.savedPlan.plan;
        return response(window.savedPlan);
      }
      if(String(url).endsWith('/plan')) {
        window.previewCalls++;
        if(window.previewMode==='hold') await new Promise(resolve=>window.releasePreview=resolve);
        if(window.previewMode==='error') return response({},503);
        if(window.previewMode==='empty') return response({plan:null,revision:0,approved:false});
        if(window.previewMode==='invalid') return response({plan:{shots:[]}});
        return response(window.savedPlan);
      }
      if(String(url).includes('/projects/')) return response({id:1,title:'Preview project',master_prompt:'নদীর ধারে',target_duration_seconds:30,status:'draft'});
      return response([]);
    };
  `,
  })
  async function evaluate(expression) {
    const result = await send('Runtime.evaluate', {
      expression,
      returnByValue: true,
      awaitPromise: true,
    })
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails))
    return result.result.value
  }
  async function waitFor(expression) {
    for (let i = 0; i < 150; i++) {
      if (await evaluate(`Boolean(${expression})`)) return
      await sleep(50)
    }
    throw new Error('UI timeout: ' + expression)
  }
  await send('Page.navigate', { url: `http://127.0.0.1:${server.address().port}/#/projects/1` })
  await waitFor(`document.querySelector('.shot-preview [role=status]')`)
  await evaluate(`window.previewMode='success'; window.releasePreview()`)
  await waitFor(`document.querySelectorAll('.shot-list li').length===6`)
  assert.deepEqual(
    await evaluate(`[...document.querySelectorAll('.shot-list h3')].map(e=>e.textContent)`),
    Array.from({ length: 6 }, (_, i) => `Shot ${i + 1} · 5 seconds`),
  )
  assert.equal(
    await evaluate(
      `[...document.querySelectorAll('.shot-prompt')].every(e=>e.value==='নদীর ধারে')`,
    ),
    true,
  )
  for (const mode of ['empty', 'error', 'invalid']) {
    await evaluate(`window.previewMode=${JSON.stringify(mode)}; location.hash='#/projects/2'`)
    if (mode === 'empty')
      await waitFor(`document.querySelector('.shot-preview').textContent.includes('No shots yet')`)
    else await waitFor(`document.querySelector('.shot-preview [role=alert]')`)
    await evaluate(`location.hash='#/projects/1'`)
    await waitFor(
      `document.querySelector('.shot-preview') && !document.querySelector('.shot-preview [role=status]')`,
    )
  }
  await evaluate(
    `window.previewMode='success'; document.querySelector('.shot-preview button').click()`,
  )
  await waitFor(`document.querySelectorAll('.shot-list li').length===6`)
  await send('Emulation.setDeviceMetricsOverride', {
    width: 390,
    height: 844,
    deviceScaleFactor: 1,
    mobile: true,
  })
  assert.equal(
    await evaluate(
      `document.querySelector('.shot-preview').scrollWidth<=document.querySelector('.shot-preview').clientWidth`,
    ),
    true,
  )
  assert.equal(await evaluate('window.renderCalls'), 0)
  const click = async (text) =>
    evaluate(
      `[...document.querySelectorAll('.plan-actions button')].find(e=>e.textContent===${JSON.stringify(text)}).click()`,
    )
  assert.equal(
    await evaluate(`document.querySelectorAll('.plan-actions button')[2].disabled`),
    true,
  )
  await evaluate(
    `(() => { const e=document.querySelector('.shot-prompt'); Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(e,'Edited নদী'); e.dispatchEvent(new Event('input',{bubbles:true})); })()`,
  )
  await evaluate('window.failSave=true')
  await click('Save plan')
  await waitFor(`document.querySelector('.shot-preview [role=alert]')`)
  assert.equal(await evaluate(`document.querySelector('.shot-prompt').value`), 'Edited নদী')
  await evaluate('window.failSave=false')
  await click('Save plan')
  await waitFor(`!document.querySelectorAll('.plan-actions button')[1].disabled`)
  await click('Approve plan')
  await waitFor(`!document.querySelectorAll('.plan-actions button')[2].disabled`)
  await click('Reload saved plan')
  await waitFor(
    `document.querySelector('.shot-prompt')?.value==='Edited নদী' && !document.querySelectorAll('.plan-actions button')[2].disabled`,
  )
  await click('Mock render')
  await waitFor(
    `document.querySelector('.shot-preview').textContent.includes('Mock render completed')`,
  )
  assert.equal(await evaluate('window.renderCalls'), 1)
  await evaluate(
    `(() => { const e=document.querySelector('.shot-prompt'); Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(e,'Changed again'); e.dispatchEvent(new Event('input',{bubbles:true})); })()`,
  )
  assert.equal(
    await evaluate(`document.querySelectorAll('.plan-actions button')[2].disabled`),
    true,
  )
  await click('Save plan')
  await waitFor(`!document.querySelectorAll('.plan-actions button')[1].disabled`)
  assert.equal(
    await evaluate(`document.querySelectorAll('.plan-actions button')[2].disabled`),
    true,
  )
  console.log(
    'PASS: loading, empty, success, errors, malformed response, retry, shot order/duration/prompt, mobile layout; edit/save failure/retry, approval, reload, mock render and edit invalidation.',
  )
} finally {
  ws?.close()
  if (chrome && chrome.exitCode === null) {
    const done = new Promise((resolve) => chrome.once('exit', resolve))
    chrome.kill()
    await done
  }
  await new Promise((resolve) => server.close(resolve))
  await fs.rm(temp, { recursive: true, force: true })
}
