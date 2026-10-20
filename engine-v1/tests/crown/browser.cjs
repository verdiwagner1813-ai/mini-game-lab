'use strict';
const fs=require('node:fs'),http=require('node:http'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {moves}=require('./harness.cjs');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright-core');
function winningPath(initial,redCrown,blueCrown){
 let best=null,seed=77;function rand(){seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;}
 for(let game=0;game<5000;game++){
  let pieces=structuredClone(initial),turn='red',path=[];
  for(let step=0;step<(best?Math.min(best.length-1,50):50);step++){
   let options=moves(pieces,turn);if(!options.length){turn=turn==='red'?'blue':'red';continue;}
   const win=options.find(m=>m.id===(turn==='red'?redCrown:blueCrown)&&m.to.x===2&&m.to.y===2);
   const m=win||options[Math.floor(rand()*options.length)];Object.assign(pieces.find(p=>p.id===m.id),m.to);path.push(m);
   if(win){best=path;break;}turn=turn==='red'?'blue':'red';
  }
 }
 assert(best,'independent solver found a legal winning sequence');return best;
}
async function layout(page){return page.locator('#board [data-piece]').evaluateAll(es=>es.map(e=>{const c=e.querySelector('circle');return{id:e.dataset.piece,team:e.dataset.piece.startsWith('R')?'red':'blue',x:(Number(c.getAttribute('cx'))-100)/100,y:(Number(c.getAttribute('cy'))-100)/100};}));}
async function start(page,touch){const b=page.locator('#startBtn');if(await b.count()&&await b.isVisible()){if(touch)await b.tap();else await b.click();}}
async function press(page,selector,touch){if(touch)await page.locator(selector).tap();else await page.locator(selector).click();}
async function reset(page,touch){await press(page,'#resetBtn',touch);if(await page.locator('#resetDialog[open]').count())await press(page,'#confirmReset',touch);await start(page,touch);}
(async()=>{
 const data=fs.readFileSync(process.argv[2]),sha256=crypto.createHash('sha256').update(data).digest('hex');
 const server=http.createServer((q,s)=>{s.setHeader('Content-Type','text/html;charset=utf-8');s.end(data);});
 await new Promise((r,j)=>{server.once('error',j);server.listen(0,'127.0.0.1',r);});let browser;
 try{
  browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
  const base='http://127.0.0.1:'+server.address().port,results=[];
  for(const viewport of [{width:1366,height:768},{width:768,height:1024},{width:360,height:800}]){
   const touch=viewport.width!==1366,context=await browser.newContext({viewport,hasTouch:touch,isMobile:touch}),page=await context.newPage(),errors=[],external=[];
   page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(!r.url().startsWith(base)&&!r.url().startsWith('data:'))external.push(r.url());});
   await page.goto(base);await start(page,touch);
   assert.equal(await page.locator('#board rect.cell').count(),25);assert.equal(await page.locator('#board .centerCell').count(),1);
   const initial=await layout(page);assert.equal(initial.length,10);assert.equal(initial.filter(p=>p.team==='red').length,5);assert.equal(initial.filter(p=>p.team==='blue').length,5);
   const crowns={red:(await page.locator('#redCrownLabel').innerText()).trim(),blue:(await page.locator('#blueCrownLabel').innerText()).trim()};assert(/^R[1-5]$/.test(crowns.red));assert(/^B[1-5]$/.test(crowns.blue));assert.equal(await page.locator('#board .crowned').count(),2);
   assert(await page.locator('#undoBtn').isDisabled());
   await press(page,'#musicBtn',touch);assert.equal(await page.locator('#musicBtn').getAttribute('aria-pressed'),'true');await page.waitForTimeout(300);await press(page,'#musicBtn',touch);assert.equal(await page.locator('#musicBtn').getAttribute('aria-pressed'),'false');
   await press(page,'#sfxBtn',touch);assert.equal(await page.locator('#sfxBtn').getAttribute('aria-pressed'),'false');await press(page,'#sfxBtn',touch);assert.equal(await page.locator('#sfxBtn').getAttribute('aria-pressed'),'true');
   await press(page,'[data-piece="B1"]',touch);assert.equal(await page.locator('.moveHint').count(),0);assert.deepEqual(await layout(page),initial);
   // Native keyboard activation followed by arrow movement on desktop; tap target on touch.
   if(!touch){await page.locator('[data-piece="R1"]').focus();await page.keyboard.press('Enter');await page.keyboard.press('ArrowRight');}
   else{await press(page,'[data-piece="R1"]',touch);assert(await page.locator('.moveHint').count()>0);await page.locator('.moveHint').first().tap();}
   const first=await layout(page);assert.deepEqual(first.find(p=>p.id==='R1'),{id:'R1',team:'red',x:3,y:0});assert((await page.locator('#status').innerText()).includes('あお'));
   await press(page,'#undoBtn',touch);assert.deepEqual(await layout(page),initial);assert((await page.locator('#status').innerText()).includes('あか'));assert.equal((await page.locator('#redCrownLabel').innerText()).trim(),crowns.red);
   // D-pad route and exact state restoration.
   await reset(page,touch);await press(page,'[data-piece="R2"]',touch);await press(page,'.dpad [data-dir="right"]',touch);assert.deepEqual((await layout(page)).find(p=>p.id==='R2'),{id:'R2',team:'red',x:3,y:1});await press(page,'#undoBtn',touch);assert.deepEqual(await layout(page),initial);
   await reset(page,touch);const red=(await page.locator('#redCrownLabel').innerText()).trim(),blue=(await page.locator('#blueCrownLabel').innerText()).trim();const path=winningPath(await layout(page),red,blue);
   for(const m of path){await press(page,'[data-piece="'+m.id+'"]',touch);const hint=page.locator('.moveHint[data-x="'+m.to.x+'"][data-y="'+m.to.y+'"]');assert.equal(await hint.count(),1,'independent destination is offered');if(touch)await hint.tap();else await page.locator('.dpad [data-dir="'+m.dir+'"]').click();assert.deepEqual((await layout(page)).find(p=>p.id===m.id),{id:m.id,team:m.id[0]==='R'?'red':'blue',...m.to});}
   assert(await page.locator('#modal').isVisible());assert((await page.locator('#modalTitle').innerText()).includes('勝ち'));assert((await page.locator('#modalText').innerText()).includes(path.at(-1).id));
   await press(page,'#closeBtn',touch);const win=await layout(page);await press(page,'[data-piece="R1"]',touch);assert.deepEqual(await layout(page),win);
   await press(page,'#undoBtn',touch);assert.equal(await page.locator('#modal').isVisible(),false);assert.notDeepEqual(await layout(page),win);assert(!(await page.locator('#status').innerText()).includes('ゲーム終了'));
   const finalMove=path.at(-1);if(!await page.locator('[data-piece="'+finalMove.id+'"] .selected').count())await press(page,'[data-piece="'+finalMove.id+'"]',touch);await press(page,'.dpad [data-dir="'+finalMove.dir+'"]',touch);assert(await page.locator('#modal').isVisible());await press(page,'#playAgainBtn',touch);assert.deepEqual(await layout(page),initial);assert(await page.locator('#undoBtn').isDisabled());
   const overflow=await page.evaluate(()=>({scrollWidth:document.documentElement.scrollWidth,innerWidth,overflow:document.documentElement.scrollWidth>innerWidth}));
   assert.deepEqual(errors,[]);assert.deepEqual(external,[]);
   assert.equal(overflow.overflow,false,'horizontal overflow');
   results.push({viewport,touch,boardCells:25,pieces:10,crownPerTeam:1,keyboard:!touch,touchTargets:touch,mouse:!touch,undo:true,reset:true,audioToggles:true,winningSequenceMoves:path.length,victoryReplay:true,overflow,errors,externalRequests:external});
   await context.close();
  }
  console.log(JSON.stringify({pass:true,sourceSha256:sha256,specific:'crown-star-catch-browser',platform:'Linux Chromium localhost HTTP',inputHTMLUnmodified:true,results,limitations:['No audible listening assertion; only actual Web Audio code execution and UI toggles','School Chromebook/Windows hardware and actual touch hardware not tested','file:// and HTTPS not tested']}));
 }finally{if(browser)await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
