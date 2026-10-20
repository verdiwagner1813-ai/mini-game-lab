'use strict';
const fs=require('node:fs'),vm=require('node:vm'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const vectors={up:[0,-1],down:[0,1],left:[-1,0],right:[1,0]};
function independentDestination(pieces,id,direction){
 const piece=pieces.find(p=>p.id===id),[dx,dy]=vectors[direction]; let x=piece.x,y=piece.y;
 for(let distance=1;distance<5;distance++){
  const nx=piece.x+distance*dx,ny=piece.y+distance*dy;
  if(nx<0||nx>=5||ny<0||ny>=5||pieces.some(p=>p.id!==id&&p.x===nx&&p.y===ny))break;
  x=nx;y=ny;
 }
 return x===piece.x&&y===piece.y?null:{x,y};
}
function moves(pieces,team){return pieces.filter(p=>p.team===team).flatMap(p=>Object.keys(vectors).flatMap(dir=>{const to=independentDestination(pieces,p.id,dir);return to?[{id:p.id,dir,to}]:[]}));}
function snapshot(value){return JSON.parse(JSON.stringify(value));}
function loadVM(filename){
 const bytes=fs.readFileSync(filename),html=bytes.toString('utf8'),scripts=[...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi)].map(m=>m[1]);
 const nodes={};
 function node(id=''){return {id,style:{},dataset:{},children:[],hidden:false,disabled:false,textContent:'',innerHTML:'',classList:{add(){},remove(){},contains(){return false}},setAttribute(){},getAttribute(){return null},append(...xs){this.children.push(...xs)},appendChild(x){this.children.push(x)},addEventListener(){},querySelectorAll(){return[]},querySelector(){return node()},focus(){},contains(){return false},getBoundingClientRect(){return{width:600,height:600}},removeAttribute(){},showModal(){this.open=true;},close(){this.open=false;},show(){this.open=true;}};}
 const document={getElementById:id=>nodes[id]??=node(id),createElementNS:(_,name)=>node(name),createElement:node,querySelectorAll:()=>[],querySelector:()=>node(),activeElement:node(),addEventListener(){}};
 const math=Object.create(Math);let random=0.1;math.random=()=>random;
 const sandbox={document,Math:math,window:{addEventListener(){},matchMedia(){return{matches:true,addEventListener(){}}}},setTimeout(){return 1},clearTimeout(){},requestAnimationFrame:f=>f(),cancelAnimationFrame(){},console};sandbox.window.window=sandbox.window;
 vm.createContext(sandbox);
 const exportCode=`window.__crownTest={get:()=>JSON.parse(JSON.stringify({state,history,selectedId,gameOver})),set:s=>{state=JSON.parse(JSON.stringify(s));history=[];selectedId=null;gameOver=false;sfxOn=false;},slide:(id,d)=>slideDestination(findPiece(id),d),legal:id=>legalMoves(findPiece(id)),move:movePiece,select:onPiece,pass:ensureTurnHasMove,undo,init:initGame,base:clonePieces(basePieces)};`;
 for(let code of scripts){if(code.includes('function slideDestination(')){assert(/\}\)\(\);\s*$/.test(code),'game IIFE recognizable');code=code.replace(/\}\)\(\);\s*$/,exportCode+'\n})();');}vm.runInContext(code,sandbox,{timeout:5000});}
 assert(sandbox.window.__crownTest,'test-only VM hook installed');
 const raw=sandbox.window.__crownTest;const api={...raw,get:()=>snapshot(raw.get()),base:snapshot(raw.base)};
 return{api,nodes,bytes,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),setRandom:x=>{random=x}};
}
module.exports={loadVM,independentDestination,moves,snapshot,vectors};
