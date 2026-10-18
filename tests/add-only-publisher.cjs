'use strict';
const assert=require('node:assert/strict');const {publish,sha,PREFIX}=require('../automation/add-only/publisher.cjs');
const html='<!doctype html><title>fixture</title>',base={runId:'test-20261018-a',html,expectedSha256:sha(html),sourceCommit:'a'.repeat(40),evidence:{testedSha256:sha(html),browser:{pass:true},logic:{pass:true}}};
function adapter(){const files=new Map([['games/exhibit-mission/index.html','ORIGINAL']]),calls=[];return {files,calls,async read(x){return files.get(x.path)??null},async create(x){assert(!('sha' in x));assert.equal(x.repository,'verdiwagner1813-ai/mini-game-lab');assert.equal(x.branch,'main');assert(x.path.startsWith(PREFIX));if(files.has(x.path))throw Error('Already exists');calls.push(x.path);files.set(x.path,x.content)}}}
(async()=>{let checks=0;let t=adapter();const r=await publish({...base,transport:t});assert(r.verifiedReadBack);assert.equal(t.files.get('games/exhibit-mission/index.html'),'ORIGINAL');assert.equal(t.calls.length,2);checks++;
await publish({...base,transport:t});assert.equal(t.calls.length,2);checks++;
t=adapter();t.files.set(PREFIX+base.runId+'/game.html','different');await assert.rejects(()=>publish({...base,transport:t}),/different content/);assert.equal(t.calls.length,0);checks++;
t=adapter();await assert.rejects(()=>publish({...base,evidence:{...base.evidence,browser:{pass:false}},transport:t}),/evidence/);assert.equal(t.calls.length,0);checks++;
t=adapter();const create=t.create.bind(t);t.create=async x=>{if(x.path.endsWith('COMPLETED.json'))throw Error('Network error');return create(x)};await assert.rejects(()=>publish({...base,transport:t}),/Network/);assert(t.files.has(PREFIX+base.runId+'/game.html'));assert(!t.files.has(PREFIX+base.runId+'/COMPLETED.json'));t.create=create;await publish({...base,transport:t});assert.equal(t.calls.length,2);checks++;
t=adapter();const c=t.create.bind(t);t.create=async x=>{await c(x);throw Error('Timeout after successful create')};await publish({...base,transport:t});assert.equal(t.calls.length,2);checks++;
t=adapter();await assert.rejects(()=>publish({...base,runId:'../escape',transport:t}),/run ID/);assert.equal(t.calls.length,0);checks++;
t=adapter();await assert.rejects(()=>publish({...base,html:html+'x',transport:t}),/hash/);assert.equal(t.calls.length,0);checks++;
console.log(JSON.stringify({pass:true,checks,writeOperation:'create only',existingOriginalUnchanged:true}));})().catch(e=>{console.error(e);process.exitCode=1});
