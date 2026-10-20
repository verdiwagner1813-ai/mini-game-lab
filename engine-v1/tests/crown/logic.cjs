'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const {loadVM,independentDestination,moves,snapshot,vectors}=require('./harness.cjs');
try{
 const {api,nodes,sha256,setRandom}=loadVM(process.argv[2]);
 const html=fs.readFileSync(process.argv[2],'utf8');
 for(const [begin,end,expected] of [['const fantasyTheme=','function clonePieces(','306c260a0150b1f7eee6001d3d107547f1ae3ff9fcce112a36f6c743124bb23d'],['function noteFreq(','board.addEventListener(','1333ef2a4f31ff361a22f25f382ceaf8beb24096bba4c465bcda4dd6fcbc5a1c']]){const i=html.indexOf(begin),j=html.indexOf(end,i);assert(i>=0&&j>i,'original audio section preserved');assert.equal(crypto.createHash('sha256').update(html.slice(i,j)).digest('hex'),expected,'original audio score and synthesis must remain unchanged');}
 let checks=0,comparisons=0,randomState=271828;
 function random(){randomState=(Math.imul(randomState,1664525)+1013904223)>>>0;return randomState/4294967296;}
 const ids=api.base.map(p=>p.id);assert.equal(ids.length,10);assert.equal(new Set(ids).size,10);
 const redCrowns=new Set(),blueCrowns=new Set();
 for(let i=0;i<5;i++){setRandom((i+.25)/5);api.init();const s=api.get().state;assert.equal(s.pieces.length,10);assert.equal(s.pieces.filter(p=>p.team==='red').length,5);assert.equal(s.pieces.filter(p=>p.team==='blue').length,5);assert.equal(s.redCrown,'R'+(i+1));assert.equal(s.blueCrown,'B'+(i+1));redCrowns.add(s.redCrown);blueCrowns.add(s.blueCrown);checks++;}
 assert.equal(redCrowns.size,5);assert.equal(blueCrowns.size,5);
 for(let n=0;n<250;n++){
  const cells=Array.from({length:25},(_,i)=>i);for(let i=24;i>0;i--){const j=Math.floor(random()*(i+1));[cells[i],cells[j]]=[cells[j],cells[i]];}
  const pieces=api.base.map((p,i)=>({...p,x:cells[i]%5,y:Math.floor(cells[i]/5)}));
  const s={pieces,turn:n%2?'red':'blue',redCrown:'R'+(n%5+1),blueCrown:'B'+(n%5+1)};
  api.set(s);
  for(const p of pieces)for(const dir of Object.keys(vectors)){assert.deepEqual(snapshot(api.slide(p.id,dir)),independentDestination(pieces,p.id,dir));comparisons++;}
  for(const team of ['red','blue'])for(const m of moves(pieces,team).slice(0,3)){
   const before={...s,turn:team};api.set(before);const expected=independentDestination(pieces,m.id,m.dir);assert.equal(api.move(m.id,m.dir),true);let after=api.get();assert.deepEqual(after.state.pieces.find(p=>p.id===m.id),{...pieces.find(p=>p.id===m.id),...expected});
   assert.equal(new Set(after.state.pieces.map(p=>p.x+','+p.y)).size,10);assert(after.state.pieces.every(p=>p.x>=0&&p.x<5&&p.y>=0&&p.y<5));api.undo();assert.deepEqual(api.get().state,snapshot(before));assert.equal(api.get().gameOver,false);checks++;
  }
  api.set(s);const enemy=pieces.find(p=>p.team!==s.turn);const before=api.get();assert.equal(api.move(enemy.id,'up'),false);assert.deepEqual(api.get(),before);checks++;
 }
 function fixture(team,crowned){
  const target=team==='red'?'R1':'B1',crown=team==='red'?'R2':'B2';
  const occupied=[{x:0,y:2},{x:3,y:2},{x:0,y:0},{x:1,y:0},{x:2,y:0},{x:3,y:0},{x:4,y:0},{x:0,y:4},{x:1,y:4},{x:4,y:4}];
  const ordered=[target,...ids.filter(id=>id!==target)];return{pieces:ordered.map((id,i)=>({id,team:id[0]==='R'?'red':'blue',...occupied[i]})),turn:team,redCrown:team==='red'?(crowned?target:crown):'R5',blueCrown:team==='blue'?(crowned?target:crown):'B5'};
 }
 for(const team of ['red','blue'])for(const crowned of [false,true]){
  api.set(fixture(team,crowned));assert.equal(api.move(team==='red'?'R1':'B1','right'),true);const s=api.get();assert.equal(s.gameOver,crowned);if(crowned){const before=snapshot(s);assert.equal(api.move(team==='red'?'R1':'B1','up'),false);assert.deepEqual(api.get(),before);assert(nodes.modalTitle.textContent.includes('勝ち'));}api.undo();assert.equal(api.get().gameOver,false);checks++;
 }
 // Packed upper-left corner traps all five red pieces while the blue border can move.
 const red=[[0,0],[1,0],[0,1],[1,1],[0,2]],blue=[[2,0],[2,1],[2,2],[1,2],[0,3]];
 const blocked={pieces:[...red.map(([x,y],i)=>({id:'R'+(i+1),team:'red',x,y})),...blue.map(([x,y],i)=>({id:'B'+(i+1),team:'blue',x,y}))],turn:'red',redCrown:'R1',blueCrown:'B1'};
 assert.equal(moves(blocked.pieces,'red').length,0);assert(moves(blocked.pieces,'blue').length>0);api.set(blocked);api.pass(false);assert.equal(api.get().state.turn,'blue');assert.equal(api.get().gameOver,false);assert(nodes.status.dataset.passMsg.includes('パス'));checks++;
 api.set(blocked);api.init();assert.equal(api.get().history.length,0);assert.equal(api.get().selectedId,null);assert.equal(api.get().gameOver,false);checks++;
 console.log(JSON.stringify({pass:true,sourceSha256:sha256,specific:'crown-star-catch-logic',randomLayouts:250,slideComparisons:comparisons,behaviorChecks:checks,randomCrownChoicesEachTeam:5,redAndBlueCrownWins:true,nonCrownCenterDoesNotWin:true,automaticPass:true,undoRestoresState:true,originalAudioSectionsHashUnchanged:true,method:'Test-only VM instrumentation of unmodified input; independent movement oracle; no production test API added',limitations:['Both-sides blocked draw unreachable with 10 pieces on 25 cells; no gameplay-rule change','No real browser in this logic test']}));
}catch(e){console.error(e);process.exitCode=1;}
