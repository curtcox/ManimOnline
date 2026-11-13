const {test}=require('node:test'),assert=require('node:assert/strict');
const {config,type}=require('../src/fragment-config.mjs');
const {createAi,parseSuite,validateReferences}=require('../vendor/fragment-kit-v0.4.3/src/ai/index.js');
const suite=require('../ai-suite.json');
test('AI deployment modes remain idle with zero default spending',async()=>{for(const [href,mode] of [[config.canonicalOrigin,'host'],[config.recoveryOrigin,'direct'],['https://unknown.example/','paste']]){let calls=0;const ai=await createAi({config,type,href,fetchSource:()=>{calls++;throw Error('Eager AI request');}});assert.equal(ai.connection,mode);assert.equal(calls,0);assert.equal(ai.budget.spent().total,0);ai.destroy();}assert.deepEqual(config.ai.budget,{total:0,day:0,month:0});});
test('data-only suite has passing good references, failing bad references and preserved state',async()=>{const parsed=parseSuite(suite,type);assert.equal(parsed.cases.length,25);await validateReferences(parsed,type);for(const c of parsed.cases.filter(c=>c.kind==='change')){for(const key of Object.keys(c.base).filter(key=>key!=='src'&&key!=='pages'))assert.deepEqual(c.reference.good[key],c.base[key]);}});
