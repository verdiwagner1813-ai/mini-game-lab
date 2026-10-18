'use strict';
const crypto=require('node:crypto');
const REPOSITORY='verdiwagner1813-ai/mini-game-lab';
const PREFIX='experiments/exhibit-seven-days/add-only-runs/';
const sha=s=>crypto.createHash('sha256').update(s,'utf8').digest('hex');
async function publish({runId,html,expectedSha256,sourceCommit,evidence,transport}){
 if(!/^[a-z0-9][a-z0-9-]{5,79}$/.test(runId))throw Error('Invalid run ID');
 if(sha(html)!==expectedSha256)throw Error('HTML hash mismatch');
 if(evidence?.browser?.pass!==true||evidence?.logic?.pass!==true||evidence.testedSha256!==expectedSha256)throw Error('Passing browser and logic evidence required');
 const base=PREFIX+runId;
 const receipt=JSON.stringify({schemaVersion:1,status:'PASS',runId,sourceCommit,gamePath:base+'/game.html',sha256:expectedSha256,evidence},null,2)+'\n';
 const results=[];
 async function ensure(path,content){
  const known=await transport.read({repository:REPOSITORY,branch:'main',path});
  if(known!==null){if(known!==content)throw Error('Existing path has different content: '+path);results.push({path,reused:true});return;}
  try{await transport.create({repository:REPOSITORY,branch:'main',path,content});}
  catch(error){const after=await transport.read({repository:REPOSITORY,branch:'main',path});if(after!==content)throw error;}
  if(await transport.read({repository:REPOSITORY,branch:'main',path})!==content)throw Error('Read-back mismatch: '+path);
  results.push({path,reused:false});
 }
 await ensure(base+'/game.html',html);
 // Completion is written LAST. An HTML-only partial run is never a passing release.
 await ensure(base+'/COMPLETED.json',receipt);
 if(await transport.read({repository:REPOSITORY,branch:'main',path:base+'/game.html'})!==html||await transport.read({repository:REPOSITORY,branch:'main',path:base+'/COMPLETED.json'})!==receipt)throw Error('Final read-back failed');
 return {status:'PASS',verifiedReadBack:true,results};
}
module.exports={publish,sha,REPOSITORY,PREFIX};
