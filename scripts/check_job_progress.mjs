// Run from the repository root after building apps/web. Uses a disposable database.
import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import { spawn } from 'node:child_process';
import assert from 'node:assert/strict';
const repo = process.cwd();
const temp = await fs.mkdtemp('/tmp/animation-jobs-');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
let api, chrome, ws, apiBase;
const server = http.createServer(async (req, res) => {
  try {
    const file = path.join(repo, 'apps/web/dist', req.url === '/' ? 'index.html' : req.url);
    res.setHeader('Content-Type', ({'.html':'text/html','.js':'text/javascript','.css':'text/css','.svg':'image/svg+xml'})[path.extname(file)] || 'application/octet-stream');
    res.end(await fs.readFile(file));
  } catch { res.writeHead(404).end(); }
});
async function launch(binary, args, expression, options = {}) {
  const child = spawn(binary, args, {stdio:['ignore','ignore','pipe'], ...options});
  try {
    const address = await new Promise((resolve, reject) => {
      let log = '';
      const timer = setTimeout(() => reject(new Error('Process startup timeout')), 15000);
      child.on('error', reject);
      child.once('exit', code => { clearTimeout(timer); reject(new Error(`Process exited ${code}: ${log}`)); });
      child.stderr.on('data', chunk => {
        log += chunk;
        const match = log.match(expression);
        if (match) { clearTimeout(timer); resolve(match[1]); }
      });
    });
    return [child, address];
  } catch (error) { child.kill(); throw error; }
}
async function startApi() {
  [api, apiBase] = await launch(path.join(repo,'.venv/bin/python'), ['-m','uvicorn','apps.api.main:app','--host','127.0.0.1','--port','0'], /Uvicorn running on (http:\/\/127\.0\.0\.1:\d+)/, {
    env:{...process.env, ANIMATION_DB_PATH:path.join(temp,'test.db'), DISABLE_REAL_PIPE:'1', PYTHONDONTWRITEBYTECODE:'1'},
  });
}
async function stop(child) {
  if(child && child.exitCode === null) {
    const done = new Promise(resolve => child.once('exit',resolve));
    child.kill();
    await done;
  }
}
try {
  await startApi();
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  let endpoint;
  [chrome, endpoint] = await launch(process.env.CHROME_BIN || '/opt/google/chrome/chrome', ['--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--no-first-run','--remote-debugging-port=0',`--user-data-dir=${temp}/chrome`,'about:blank'], /DevTools listening on (ws:\/\/\S+)/);
  ws = new WebSocket(endpoint);
  await new Promise(resolve => ws.addEventListener('open', resolve, {once:true}));
  let id=0, sessionId, holdJobs=true, failJobs=false, holdCreate=true, failCreate=false, holdTicks=false, useDemo=false, failResult=false, providerError=false;
  let heldJobs=[], heldCreate=[], createCount=0, tickCount=0;
  let failCancel=false, holdCancel=false, heldCancel=[], cancelCount=0;
  let holdDetails=false, heldDetails=[], failDetails=false;
  let navigationGeneration=0, cancelledNavigationResponses=0;
  let holdCharacters=false, heldCharacters=[], failCharacters=false, holdCharacterSave=false, heldCharacterSave=[], failCharacterSave=false, characterSaves=0;
  let holdVoices=false, heldVoices=[], failVoices=false, holdVoiceSave=false, heldVoiceSave=[], failVoiceSave=false, voiceSaves=0;
  let holdSettings=false, heldSettings=[], failSettings=false, emptySettings=false;
  let artifactGate, releaseArtifacts, artifactWaiters=0, failArtifact='', invalidArtifact='', failDownload=false;
  let downloadGate, releaseDownload, downloadRequests=0;
  const artifactReads={image:0,audio:0,video:0}, downloads=[];
  const pending=new Map(), errors=[], abortedRequests=new Set();
  const forwarding=new Set();
  function send(method,params={}) {
    return new Promise((resolve,reject) => {
      const key=++id;
      const timer=setTimeout(()=>{pending.delete(key);reject(new Error(`CDP timeout: ${method}`));},15000);
      pending.set(key,{resolve,reject,timer});
      ws.send(JSON.stringify({id:key,method,params,...(sessionId && !method.startsWith('Browser.') ? {sessionId} : {})}));
    });
  }
  function reply(requestId,body,responseCode=200) {
    return send('Fetch.fulfillRequest',{requestId,responseCode,responseHeaders:[{name:'Content-Type',value:'application/json'},{name:'Access-Control-Allow-Origin',value:'*'},{name:'Access-Control-Allow-Headers',value:'content-type'}],body:Buffer.from(JSON.stringify(body)).toString('base64')});
  }
  async function forward(p) {
    const work=(async () => {
      const url=new URL(p.request.url);
      const response=await fetch(apiBase+url.pathname+url.search,{method:p.request.method,headers:{'Content-Type':'application/json'},...(p.request.postData ? {body:p.request.postData} : {})});
      const headers=[...response.headers].filter(([name])=>['content-type','content-disposition','cache-control','x-content-type-options'].includes(name)).map(([name,value])=>({name,value}));
      headers.push({name:'Access-Control-Allow-Origin',value:'*'});
      return send('Fetch.fulfillRequest',{requestId:p.requestId,responseCode:response.status,responseHeaders:headers,body:Buffer.from(await response.arrayBuffer()).toString('base64')});
    })();
    forwarding.add(work);
    try { return await work; } finally { forwarding.delete(work); }
  }
  async function route(p) {
    const pathname=new URL(p.request.url).pathname;
    if(p.request.method==='OPTIONS') return reply(p.requestId,{});
    const artifact=pathname.match(/\/artifacts\/(image|audio|video)$/)?.[1];
    if(artifact) {
      if(new URL(p.request.url).searchParams.get('download')==='true') {
        downloadRequests++;
        if(downloadGate) await downloadGate;
        if(failDownload) return reply(p.requestId,{detail:'Missing file'},410);
      } else {
        artifactReads[artifact]++;
        if(artifactGate) { artifactWaiters++; await artifactGate; }
        if(failArtifact===artifact) return reply(p.requestId,{detail:'Missing file'},410);
        if(invalidArtifact===artifact) return send('Fetch.fulfillRequest',{requestId:p.requestId,responseCode:200,responseHeaders:[{name:'Content-Type',value:'image/png'},{name:'Access-Control-Allow-Origin',value:'*'}],body:Buffer.from('invalid image bytes').toString('base64')});
      }
    }
    if(pathname==='/settings' && p.request.method==='GET') {
      if(failSettings) return reply(p.requestId,{detail:'Unavailable'},503);
      if(emptySettings) return reply(p.requestId,{});
      if(holdSettings) { heldSettings.push(p); return; }
    }
    if(pathname==='/characters' && p.request.method==='GET') {
      if(failCharacters) return reply(p.requestId,{detail:'Unavailable'},503);
      if(holdCharacters) { heldCharacters.push(p); return; }
    }
    if(pathname==='/characters' && p.request.method==='POST') {
      characterSaves++;
      if(failCharacterSave) return reply(p.requestId,{detail:'Rejected'},422);
      if(holdCharacterSave) { heldCharacterSave.push(p); return; }
    }
    if(pathname==='/voices' && p.request.method==='GET') {
      if(failVoices) return reply(p.requestId,{detail:'Unavailable'},503);
      if(holdVoices) { heldVoices.push(p); return; }
    }
    if(pathname==='/voices' && p.request.method==='POST') {
      voiceSaves++;
      if(failVoiceSave) return reply(p.requestId,{detail:'Rejected'},422);
      if(holdVoiceSave) { heldVoiceSave.push(p); return; }
    }
    if(/^\/projects\/\d+$/.test(pathname)) {
      if(failDetails) return reply(p.requestId,{detail:'Unavailable'},503);
      if(holdDetails) { heldDetails.push(p); return; }
    }
    if(pathname.endsWith('/result')) {
      if(failResult) return reply(p.requestId,{detail:'Unavailable'},503);
      if(providerError) return reply(p.requestId,{result:null,error:{code:'dependency_missing',message:'ffmpeg is unavailable'}});
    }
    if(pathname==='/jobs') {
      if(failJobs) return reply(p.requestId,{detail:'Unavailable'},503);
      if(holdJobs) { heldJobs.push(p); return; }
    }
    if(pathname.endsWith('/tick')) {
      if(holdTicks) return send('Fetch.failRequest',{requestId:p.requestId,errorReason:'Aborted'});
      tickCount++;
    }
    if(pathname.endsWith('/cancel')) {
      cancelCount++;
      if(failCancel) return reply(p.requestId,{detail:'Cancel unavailable'},503);
      if(holdCancel) { heldCancel.push(p); return; }
    }
    if(p.request.method==='POST' && /\/projects\/\d+\/fixture-jobs$/.test(pathname)) {
      createCount++;
      if(failCreate) return reply(p.requestId,{detail:'Rejected'},422);
      if(holdCreate) { heldCreate.push(p); return; }
      // Slow/manual legacy jobs exercise cancellation without racing the fast fixture worker.
      if(useDemo) p = {...p, request: {...p.request, url: p.request.url.replace('/fixture-jobs', '/jobs')}};
    }
    return forward(p);
  }
  ws.addEventListener('message',event => {
    const data=JSON.parse(event.data);
    if(data.id) {
      const item=pending.get(data.id); pending.delete(data.id);
      if(item) clearTimeout(item.timer);
      if(data.error) item?.reject(new Error(JSON.stringify(data.error))); else item?.resolve(data.result);
    } else if(data.method==='Fetch.requestPaused') {
      const generation=navigationGeneration;
      route(data.params).catch(async error=>{
        // Chrome discards interception IDs when navigation cancels a request.
        // A component may also explicitly abort a stale poll without navigation.
        // Require observed navigation or a matching Network cancellation event.
        const discarded=error.message === '{"code":-32602,"message":"Invalid InterceptionId."}';
        if(discarded) await sleep(50);
        if(discarded && (generation !== navigationGeneration || abortedRequests.has(data.params.networkId))) {
          cancelledNavigationResponses++;
        } else errors.push(`${data.params.request.method} ${data.params.request.url}: ${error.message}`);
      });
    }
    else if(data.method==='Page.frameNavigated' || data.method==='Page.navigatedWithinDocument') navigationGeneration++;
    else if(data.method==='Network.loadingFailed' && data.params.canceled) abortedRequests.add(data.params.requestId);
    else if(data.method==='Runtime.exceptionThrown') errors.push(data.params.exceptionDetails.exception?.description || data.params.exceptionDetails.text);
    else if(data.method==='Browser.downloadWillBegin') downloads.push(data.params);
  });
  const target=await send('Target.createTarget',{url:'about:blank'});
  sessionId=(await send('Target.attachToTarget',{targetId:target.targetId,flatten:true})).sessionId;
  await send('Runtime.enable'); await send('Page.enable'); await send('Network.enable');
  await send('Page.addScriptToEvaluateOnNewDocument',{source:`
    window.__mediaUrls = new Set();
    const create = URL.createObjectURL.bind(URL), revoke = URL.revokeObjectURL.bind(URL);
    URL.createObjectURL = blob => { const url = create(blob); window.__mediaUrls.add(url); return url; };
    URL.revokeObjectURL = url => { window.__mediaUrls.delete(url); revoke(url); };
  `});
  await fs.mkdir(path.join(temp,'downloads'));
  await send('Browser.setDownloadBehavior',{behavior:'allow',downloadPath:path.join(temp,'downloads'),eventsEnabled:true});
  await send('Fetch.enable',{patterns:[{urlPattern:'http://127.0.0.1:8000/*'}]});
  async function evaluate(expression) {
    const result=await send('Runtime.evaluate',{expression,returnByValue:true,userGesture:true,awaitPromise:true});
    if(result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  }
  async function waitFor(expression) {
    for(let i=0;i<150;i++) { if(await evaluate(`Boolean(${expression})`)) return; await sleep(50); }
    throw new Error(`UI timeout: ${expression}`);
  }
  async function restartApi() {
    const url=await evaluate('location.href');
    // Leave the page and drain forwarding before stopping the test server.
    // route() still records any unexpected forwarding error.
    await send('Page.navigate',{url:'about:blank'});
    await waitFor(`location.href === 'about:blank'`);
    await Promise.allSettled([...forwarding]);
    await stop(api); await startApi();
    await send('Page.navigate',{url});
  }
  await send('Page.navigate',{url:`http://127.0.0.1:${server.address().port}/`});
  await waitFor(`document.querySelector('.jobs-panel')?.innerText.includes('Loading jobs')`);
  while(!heldJobs.length) await sleep(25);
  holdJobs=false; for(const request of heldJobs) await forward(request);
  await waitFor(`document.querySelector('.jobs-panel').innerText.includes('No jobs yet.')`);
  await waitFor(`document.body.innerText.includes('API connected')`);
  console.log('PASS: loading and empty states');
  await evaluate(`(() => { const input=document.querySelector('input[name=title]'); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,'Demo persistence check'); input.dispatchEvent(new Event('input',{bubbles:true})); })()`);
  await evaluate(`(() => { const input=document.querySelector('textarea[name=master_prompt]'); Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(input,'A quiet rooftop'); input.dispatchEvent(new Event('input',{bubbles:true})); })()`);
  await evaluate(`document.querySelector('button[type=submit]').click()`);
  await waitFor(`document.querySelector('.job-actions button') && !document.querySelector('.job-actions button').disabled`);
  await evaluate(`document.querySelector('.job-actions button').click()`);
  await waitFor(`document.querySelector('.job-actions button').innerText.includes('Starting')`);
  await evaluate(`document.querySelector('.job-actions button').click()`);
  while(!heldCreate.length) await sleep(25);
  assert.equal(createCount,1);
  artifactGate=new Promise(resolve=>{releaseArtifacts=resolve;});
  holdCreate=false; for(const request of heldCreate) await forward(request);
  await waitFor(`document.querySelector('.jobs-list').innerText.includes('Sample ready')`);
  await waitFor(`document.querySelectorAll('.artifact-preview [role=status]').length === 3`);
  assert.equal(await evaluate(`document.querySelector('video') === null`),true);
  while(artifactWaiters<3) await sleep(25);
  releaseArtifacts(); artifactGate=null;
  const previewsReady=`document.querySelector('.artifact-preview img')?.naturalWidth > 0 && document.querySelector('video')?.readyState >= 2 && document.querySelector('audio')?.readyState >= 2 && !document.querySelector('.artifact-preview [role=status]')`;
  await waitFor(previewsReady);
  assert.equal(await evaluate(`document.querySelector('video').autoplay || document.querySelector('audio').autoplay`),false);
  await evaluate(`document.querySelector('video').scrollIntoView({block:'center'})`);
  await sleep(100);
  await evaluate(`(async () => {
    const video = document.querySelector('video');
    try { await video.play(); }
    catch (error) {
      // The existing one-frame/one-second fixture can end before Chrome resolves
      // play(). Accept only that exact, observed terminal playback condition.
      if (!(error.name === 'AbortError' && error.message.includes('interrupted by end of playback')
        && video.ended && video.currentTime >= video.duration && !video.error)) throw error;
    }
  })()`);
  await waitFor(`document.querySelector('video').currentTime > 0`);
  await evaluate(`document.querySelector('video').pause(); document.querySelector('audio').scrollIntoView({block:'center'})`);
  await sleep(100);
  await evaluate(`document.querySelector('audio').play()`);
  await waitFor(`document.querySelector('audio').currentTime > 0`);
  await evaluate(`document.querySelector('audio').pause()`);
  const stableUrls=await evaluate(`Array.from(document.querySelectorAll('.artifact-preview img, .artifact-preview video, .artifact-preview audio'), element => element.src)`);
  const readsBefore={...artifactReads};
  await sleep(2300);
  assert.deepEqual(artifactReads,readsBefore);
  assert.deepEqual(await evaluate(`Array.from(document.querySelectorAll('.artifact-preview img, .artifact-preview video, .artifact-preview audio'), element => element.src)`),stableUrls);
  assert.equal(await evaluate(`window.__mediaUrls.size`),3);
  console.log('PASS: preview loading, real image/video/audio decoding and playback; polling keeps stable media URLs');
  for(const [kind,name] of [['image','sample_image.png'],['audio','silent_audio.wav'],['video','sample_video.mp4']]) {
    await evaluate(`document.querySelector('[aria-label="Download ${kind} for job 1"]').click()`);
    await waitFor(`document.querySelector('[data-artifact-kind="${kind}"]').innerText.includes('Download started.')`);
    const filename=`job-1-${kind}.${name.split('.').at(-1)}`;
    let saved;
    for(let attempt=0;attempt<150;attempt++) {
      try { saved=await fs.readFile(path.join(temp,'downloads',filename)); break; } catch { await sleep(50); }
    }
    assert.deepEqual(saved,await fs.readFile(path.join(repo,'tests/fixtures',name)));
    assert.ok(downloads.some(item=>item.suggestedFilename===filename));
  }
  assert.equal(downloadRequests,3);
  console.log('PASS: all three browser downloads have safe filenames and exact fixture bytes');
  assert.equal(tickCount,0);
  const stored=await (await fetch(apiBase+'/jobs')).json();
  assert.equal(stored[0].state,'completed');
  assert.ok((await (await fetch(apiBase+'/jobs/1/result')).json()).result.video);
  await send('Page.reload');
  await waitFor(`document.querySelector('.jobs-list')?.innerText.includes('Sample ready')`);
  await waitFor(previewsReady);
  assert.equal(createCount,1);
  await restartApi();
  await waitFor(`document.querySelector('.jobs-list')?.innerText.includes('Sample ready')`);
  await waitFor(previewsReady);
  console.log('PASS: real fixture submission, saved result, refresh/restart and no browser ticks');
  failArtifact='video';
  await send('Page.reload');
  await waitFor(`document.querySelector('[data-artifact-kind="video"] [role=alert]')?.innerText.includes('410')`);
  await waitFor(`document.querySelector('.artifact-preview img')?.naturalWidth > 0 && document.querySelector('audio')?.readyState >= 2`);
  assert.equal(await evaluate(`document.querySelector('[data-artifact-kind="video"] video') === null`),true);
  failArtifact='';
  await evaluate(`document.querySelector('[aria-label="Retry video preview for job 1"]').click()`);
  await waitFor(previewsReady);
  invalidArtifact='image';
  await send('Page.reload');
  await waitFor(`document.querySelector('[data-artifact-kind="image"] [role=alert]')?.innerText.includes('preview')`);
  invalidArtifact='';
  await evaluate(`document.querySelector('[aria-label="Retry image preview for job 1"]').click()`);
  await waitFor(previewsReady);
  failDownload=true;
  downloadGate=new Promise(resolve=>{releaseDownload=resolve;});
  const downloadCountBefore=downloadRequests;
  await evaluate(`document.querySelector('[aria-label="Download video for job 1"]').click()`);
  await waitFor(`document.querySelector('[aria-label="Download video for job 1"]').disabled`);
  await evaluate(`document.querySelector('[aria-label="Download video for job 1"]').click()`);
  while(downloadRequests===downloadCountBefore) await sleep(25);
  assert.equal(downloadRequests,downloadCountBefore+1);
  releaseDownload(); downloadGate=null;
  await waitFor(`document.querySelector('.artifact-download-error')?.innerText.includes('410')`);
  assert.equal(await evaluate(`document.querySelector('video').readyState >= 2`),true);
  failDownload=false;
  await evaluate(`document.querySelector('[aria-label="Download video for job 1"]').click()`);
  await waitFor(`document.querySelector('[data-artifact-kind="video"]').innerText.includes('Download started.') && !document.querySelector('.artifact-download-error')`);
  console.log('PASS: missing-media and decode errors are isolated; preview and download retry; duplicate download guard');
  await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});
  await sleep(200);
  assert.equal(await evaluate(`document.documentElement.scrollWidth <= window.innerWidth`),true,
    JSON.stringify(await evaluate(`Array.from(document.querySelectorAll('body *')).filter(element => element.getBoundingClientRect().right > window.innerWidth + 1).map(element => [element.tagName, element.className, element.getBoundingClientRect().width]).slice(0, 15)`)));
  await evaluate(`document.querySelector('.sample-artifacts').scrollIntoView(); window.scrollBy(0, -150)`);
  const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  await fs.writeFile(path.join(temp,'sample-preview-mobile.png'),Buffer.from(shot.data,'base64'));
  await send('Emulation.setDeviceMetricsOverride',{width:1280,height:900,deviceScaleFactor:1,mobile:false});
  await evaluate(`document.querySelector('.sample-artifacts').scrollIntoView(); window.scrollBy(0, -150)`);
  const desktop=await send('Page.captureScreenshot',{format:'png'});
  await fs.writeFile(path.join(temp,'sample-preview-desktop.png'),Buffer.from(desktop.data,'base64'));
  await evaluate(`location.hash = '#/settings'`);
  await waitFor(`document.querySelector('.settings-page') && window.__mediaUrls.size === 0`);
  artifactWaiters=0;
  artifactGate=new Promise(resolve=>{releaseArtifacts=resolve;});
  await evaluate(`location.hash = '#/'`);
  await waitFor(`document.querySelectorAll('.artifact-preview [role=status]').length === 3`);
  while(artifactWaiters<3) await sleep(25);
  await evaluate(`location.hash = '#/settings'`);
  await waitFor(`document.querySelector('.settings-page')`);
  releaseArtifacts(); artifactGate=null;
  await sleep(200);
  assert.equal(await evaluate(`window.__mediaUrls.size`),0);
  await evaluate(`location.hash = '#/'`);
  await waitFor(previewsReady);
  assert.equal(createCount,1);
  assert.equal(tickCount,0);
  console.log(`PASS: mobile layout, URL cleanup and leaving during loading; screenshots: ${temp}`);
  failJobs=true;
  await send('Page.reload');
  await waitFor(`document.querySelector('.jobs-panel [role=alert]')?.innerText.includes('503')`);
  failJobs=false;
  await send('Page.reload');
  await waitFor(`document.querySelector('.jobs-list')?.innerText.includes('Sample ready')`);
  await waitFor(`!document.querySelector('.job-actions button').disabled`);
  failResult=true;
  await send('Page.reload');
  await waitFor(`document.querySelector('.jobs-list [role=alert]')?.innerText.includes('503')`);
  assert.equal(await evaluate(`document.querySelector('progress').value`),100);
  failResult=false; providerError=true;
  await waitFor(`document.querySelector('.jobs-list [role=alert]')?.innerText.includes('ffmpeg is unavailable')`);
  providerError=false;
  await waitFor(`document.querySelector('.jobs-list').innerText.includes('Sample ready') && !document.querySelector('.jobs-list [role=alert]')`);
  console.log('PASS: result fetch errors preserve progress, retry and display provider failures');
  useDemo=true;
  failCreate=true;
  await evaluate(`document.querySelector('.job-actions button').click()`);
  await waitFor(`document.querySelector('.jobs-panel [role=alert]')?.innerText.includes('422')`);
  await waitFor(`!document.querySelector('.job-actions button').disabled`);
  assert.equal((await (await fetch(apiBase+'/jobs')).json()).length,1);
  failCreate=false;
  await evaluate(`document.querySelector('.job-actions button').click()`);
  await waitFor(`document.querySelector('[data-job-id="2"] button') && !document.querySelector('[data-job-id="2"] button').disabled`);
  failCancel=true;
  await evaluate(`document.querySelector('[data-job-id="2"] button').click()`);
  await waitFor(`document.querySelector('.jobs-panel [role=alert]')?.innerText.includes('503')`);
  await waitFor(`document.querySelector('[data-job-id="2"] button') && !document.querySelector('[data-job-id="2"] button').disabled`);
  assert.equal((await (await fetch(apiBase+'/jobs')).json())[1].state,'running');
  console.log('PASS: failed cancellation remains running and can be retried');
  failCancel=false; holdCancel=true;
  await evaluate(`document.querySelector('[data-job-id="2"] button').click()`);
  await waitFor(`document.querySelector('[data-job-id="2"] button').innerText.includes('Cancelling')`);
  await evaluate(`document.querySelector('[data-job-id="2"] button').click()`);
  while(!heldCancel.length) await sleep(25);
  assert.equal(cancelCount,2);
  holdCancel=false; for(const request of heldCancel) await forward(request);
  await waitFor(`document.querySelector('[data-job-id="2"]').innerText.includes('Cancelled. Progress has stopped.')`);
  assert.equal(await evaluate(`document.querySelector('[data-job-id="2"] button') === null`),true);
  const cancelled=(await (await fetch(apiBase+'/jobs')).json())[1];
  await restartApi();
  await waitFor(`document.querySelector('[data-job-id="2"]')?.innerText.includes('Cancelled. Progress has stopped.')`);
  const stoppedTicks=tickCount;
  await sleep(2300);
  assert.equal(tickCount,stoppedTicks);
  assert.deepEqual((await (await fetch(apiBase+'/jobs')).json())[1],cancelled);
  console.log('PASS: cancelling state, duplicate-click guard, cancellation survives refresh/restart without further ticks');
  const third=await (await fetch(apiBase+'/projects/1/jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();
  await send('Page.reload');
  await waitFor(`document.querySelector('[data-job-id="${third.id}"] progress')?.value === 5`);
  assert.deepEqual((await (await fetch(apiBase+'/jobs')).json())[1],cancelled);
  assert.equal(tickCount,0);
  console.log('PASS: legacy jobs remain read-only while cancelled progress stays fixed');
  const secondProject=await (await fetch(apiBase+'/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title:'Workspace isolation',master_prompt:'Night scene\nA quiet rooftop',target_duration_seconds:45})})).json();
  holdDetails=true;
  await evaluate(`location.hash = '#/projects/${secondProject.id}'`);
  await waitFor(`document.body.innerText.includes('Loading project')`);
  while(!heldDetails.length) await sleep(25);
  holdDetails=false; for(const request of heldDetails) await forward(request);
  await waitFor(`document.querySelector('.workspace h1')?.innerText === 'Workspace isolation' && document.body.innerText.includes('No jobs yet.')`);
  assert.equal(await evaluate(`document.querySelector('.master-prompt').innerText`),'Night scene\nA quiet rooftop');
  assert.equal(await evaluate(`document.querySelector('.project-details').innerText.includes('45 seconds')`),true);
  assert.equal(await evaluate(`document.querySelectorAll('.jobs-list li').length`),0);
  const otherBefore=(await (await fetch(apiBase+'/jobs')).json()).find(job=>job.id===third.id).progress;
  await evaluate(`document.querySelector('.job-actions button').click()`);
  await waitFor(`document.querySelector('.workspace progress')?.value === 5`);
  const workspaceJob=(await (await fetch(apiBase+'/jobs')).json()).find(job=>job.project_id===secondProject.id);
  assert.equal((await (await fetch(apiBase+'/jobs')).json()).find(job=>job.id===third.id).progress,otherBefore);
  assert.equal(await evaluate(`document.querySelectorAll('.jobs-list li').length`),1);
  console.log('PASS: workspace loading, details, empty state and project-only progress');
  await evaluate(`document.querySelector('.jobs-list button').click()`);
  await waitFor(`document.querySelector('.jobs-list').innerText.includes('Cancelled. Progress has stopped.')`);
  await send('Page.reload');
  await waitFor(`document.querySelector('.workspace h1')?.innerText === 'Workspace isolation' && document.querySelector('.jobs-list')?.innerText.includes('Cancelled. Progress has stopped.')`);
  assert.equal(await evaluate(`document.querySelector('.jobs-list li').dataset.jobId`),String(workspaceJob.id));
  console.log('PASS: workspace cancellation and direct URL reload');
  failDetails=true;
  await send('Page.reload');
  await waitFor(`document.querySelector('.workspace [role=alert]')?.innerText.includes('503')`);
  assert.equal(await evaluate(`document.querySelector('.jobs-panel') === null`),true);
  failDetails=false;
  await evaluate(`document.querySelector('.workspace button').click()`);
  await waitFor(`document.querySelector('.workspace h1')?.innerText === 'Workspace isolation'`);
  await evaluate(`document.querySelector('.workspace > a').click()`);
  await waitFor(`document.querySelector('.projects-list a[href="#/projects/${secondProject.id}"]')`);
  await evaluate(`document.querySelector('.projects-list a[href="#/projects/${secondProject.id}"]').click()`);
  await waitFor(`document.querySelector('.workspace h1')?.innerText === 'Workspace isolation'`);
  await evaluate(`history.back()`);
  await waitFor(`document.querySelector('.home-panel input[name=title]')`);
  console.log('PASS: workspace error/retry, saved-project link and browser Back');
  await evaluate(`location.hash = '#/projects/999999'`);
  await waitFor(`document.querySelector('.workspace [role=alert]')?.innerText === 'Project not found.'`);
  await evaluate(`location.hash = '#/projects/invalid'`);
  await waitFor(`document.querySelector('h1')?.innerText === 'Page not found'`);
  console.log('PASS: missing project and invalid route');
  await evaluate(`location.hash = '#/'`);
  await waitFor(`document.querySelector('.home-panel') && document.querySelector('nav a[href="#/characters"]')`);
  holdCharacters=true;
  await evaluate(`document.querySelector('nav a[href="#/characters"]').click()`);
  await waitFor(`document.body.innerText.includes('Loading characters')`);
  while(!heldCharacters.length) await sleep(25);
  holdCharacters=false; for(const request of heldCharacters) await forward(request);
  await waitFor(`document.body.innerText.includes('No characters yet.')`);
  async function fillCharacter(name, description) {
    await evaluate(`(() => {
      const input=document.querySelector('input[name=name]');
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,${JSON.stringify(name)});
      input.dispatchEvent(new Event('input',{bubbles:true}));
      const area=document.querySelector('textarea');
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(area,${JSON.stringify(description)});
      area.dispatchEvent(new Event('input',{bubbles:true}));
    })()`);
  }
  await fillCharacter('Airi browser test','Blue hair\nRed jacket');
  holdCharacterSave=true;
  await evaluate(`document.querySelector('button[type=submit]').click()`);
  await waitFor(`document.querySelector('button[type=submit]').innerText.includes('Saving')`);
  await evaluate(`document.querySelector('button[type=submit]').click()`);
  while(!heldCharacterSave.length) await sleep(25);
  assert.equal(characterSaves,1);
  holdCharacterSave=false; for(const request of heldCharacterSave) await forward(request);
  await waitFor(`document.body.innerText.includes('Character saved: Airi browser test')`);
  assert.equal(await evaluate(`document.querySelector('.character-list p').innerText`),'Blue hair\nRed jacket');
  await restartApi();
  await waitFor(`document.querySelector('.character-list h3')?.innerText === 'Airi browser test'`);
  console.log('PASS: Characters navigation, loading/empty, saving, duplicate guard, refresh/restart persistence');
  failCharacters=true; await send('Page.reload');
  await waitFor(`document.querySelector('[role=alert]')?.innerText.includes('503')`);
  failCharacters=false;
  await evaluate(`Array.from(document.querySelectorAll('button')).find(button=>button.innerText==='Retry').click()`);
  await waitFor(`!document.querySelector('button[type=submit]').disabled`);
  failCharacterSave=true; await fillCharacter('Retry profile','Keep this input');
  await evaluate(`document.querySelector('button[type=submit]').click()`);
  await waitFor(`document.querySelector('[role=alert]')?.innerText.includes('422')`);
  await waitFor(`!document.querySelector('button[type=submit]').disabled`);
  assert.equal(await evaluate(`document.querySelector('input[name=name]').value`),'Retry profile');
  assert.equal((await (await fetch(apiBase+'/characters')).json()).length,1);
  console.log('PASS: Characters list retry and save error preserve input without duplicate data');
  await evaluate(`location.hash = '#/'`);
  await waitFor(`document.querySelector('.home-panel') && document.querySelector('nav a[href="#/voices"]')`);
  holdVoices=true;
  await evaluate(`document.querySelector('nav a[href="#/voices"]').click()`);
  await waitFor(`document.body.innerText.includes('Loading voices')`);
  while(!heldVoices.length) await sleep(25);
  holdVoices=false; for(const request of heldVoices) await forward(request);
  await waitFor(`document.body.innerText.includes('No voices yet.')`);
  async function fillVoice(name, style) {
    await evaluate(`(() => {
      const input=document.querySelector('input[name=name]');
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(input,${JSON.stringify(name)});
      input.dispatchEvent(new Event('input',{bubbles:true}));
      const language=document.querySelector('input[name=language]');
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(language,'বাংলা');
      language.dispatchEvent(new Event('input',{bubbles:true}));
      const area=document.querySelector('textarea');
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,'value').set.call(area,${JSON.stringify(style)});
      area.dispatchEvent(new Event('input',{bubbles:true}));
    })()`);
  }
  await fillVoice('Narrator browser test','Calm\nWarm');
  holdVoiceSave=true;
  await evaluate(`document.querySelector('button[type=submit]').click()`);
  await waitFor(`document.querySelector('button[type=submit]').innerText.includes('Saving')`);
  await evaluate(`document.querySelector('button[type=submit]').click()`);
  while(!heldVoiceSave.length) await sleep(25);
  assert.equal(voiceSaves,1);
  holdVoiceSave=false; for(const request of heldVoiceSave) await forward(request);
  await waitFor(`document.body.innerText.includes('Voice saved: Narrator browser test')`);
  assert.equal(await evaluate(`document.querySelector('.voice-list .master-prompt').innerText`),'Calm\nWarm');
  assert.equal((await (await fetch(apiBase+'/voices')).json())[0].language,'বাংলা');
  assert.equal(await evaluate(`document.querySelector('input[name=language]').value`),'');
  await restartApi();
  await waitFor(`document.querySelector('.voice-list h3')?.innerText === 'Narrator browser test'`);
  console.log('PASS: Voices navigation, loading/empty, saving, duplicate guard, refresh/restart persistence');
  failVoices=true; await send('Page.reload');
  await waitFor(`document.querySelector('[role=alert]')?.innerText.includes('503')`);
  failVoices=false;
  await evaluate(`Array.from(document.querySelectorAll('button')).find(button=>button.innerText==='Retry').click()`);
  await waitFor(`!document.querySelector('button[type=submit]').disabled`);
  failVoiceSave=true; await fillVoice('Retry profile','Keep this input');
  await evaluate(`document.querySelector('button[type=submit]').click()`);
  await waitFor(`document.querySelector('[role=alert]')?.innerText.includes('422')`);
  await waitFor(`!document.querySelector('button[type=submit]').disabled`);
  assert.equal(await evaluate(`document.querySelector('input[name=name]').value`),'Retry profile');
  assert.equal((await (await fetch(apiBase+'/voices')).json()).length,1);
  console.log('PASS: Voices list retry and save error preserve input without duplicate data');
  assert.equal(await evaluate(`document.querySelector('input[name=language]').value`),'বাংলা');
  assert.equal(await evaluate(`document.querySelector('textarea[name=style]').value`),'Keep this input');
  failVoiceSave=false;
  await evaluate(`document.querySelector('button[type=submit]').click()`);
  await waitFor(`document.body.innerText.includes('Voice saved: Retry profile')`);
  assert.equal((await (await fetch(apiBase+'/voices')).json()).length,2);
  console.log('PASS: Voices successful retry after failed save');
  await evaluate(`location.hash = '#/'`);
  await waitFor(`document.querySelector('.home-panel') && document.querySelector('nav a[href="#/settings"]')`);
  holdSettings=true;
  await evaluate(`document.querySelector('nav a[href="#/settings"]').click()`);
  await waitFor(`document.querySelector('.settings-page [role=status]')?.innerText.includes('Loading settings')`);
  assert.equal(await evaluate(`document.querySelector('.database-path') === null`),true);
  while(!heldSettings.length) await sleep(25);
  holdSettings=false; for(const request of heldSettings) await forward(request);
  const expectedDatabasePath=path.join(temp,'test.db');
  await waitFor(`document.querySelector('.database-path')?.textContent === ${JSON.stringify(expectedDatabasePath)}`);
  assert.equal(await evaluate(`document.querySelectorAll('.settings-page input, .settings-page form').length`),0);
  await restartApi();
  await waitFor(`document.querySelector('.database-path')?.textContent === ${JSON.stringify(expectedDatabasePath)}`);
  console.log('PASS: Settings navigation, loading, exact database path, read-only UI and refresh/restart');
  failSettings=true; await send('Page.reload');
  await waitFor(`document.querySelector('.settings-page [role=alert]')?.innerText.includes('503')`);
  assert.equal(await evaluate(`document.querySelector('.database-path') === null`),true);
  failSettings=false;
  await evaluate(`document.querySelector('.settings-page button').click()`);
  await waitFor(`document.querySelector('.database-path')?.textContent === ${JSON.stringify(expectedDatabasePath)}`);
  emptySettings=true; await send('Page.reload');
  await waitFor(`document.querySelector('.settings-page [role=alert]')?.innerText.includes('Database path is missing')`);
  emptySettings=false;
  await evaluate(`document.querySelector('.settings-page button').click()`);
  await waitFor(`document.querySelector('.database-path')?.textContent === ${JSON.stringify(expectedDatabasePath)}`);
  await evaluate(`document.querySelector('.settings-page > a').click()`);
  await waitFor(`document.querySelector('.home-panel') && document.querySelector('nav a[href="#/settings"]')`);
  await evaluate(`history.back()`);
  await waitFor(`document.querySelector('.database-path')?.textContent === ${JSON.stringify(expectedDatabasePath)}`);
  console.log('PASS: Settings HTTP error/retry, missing-path error/retry and browser Back');
  assert.deepEqual(errors,[]);
  console.log(`Observed navigation/abort-cancelled interception responses: ${cancelledNavigationResponses}`);
  console.log('PASS: create error recovery; no browser exceptions; real API and disposable SQLite');
} finally {
  ws?.close(); server.close(); await stop(chrome); await stop(api);
}
