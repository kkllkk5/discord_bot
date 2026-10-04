import test from 'node:test';
import assert from 'node:assert/strict';
import {DashboardController,validateAction,filterLogs} from '../assets/controller.js';
import {HttpAdapter} from '../assets/adapter.js';

test('confirmation controller rejects unsupported controls, cancelled and unchecked execution',async()=>{
 for(const kind of ['start','stop','restart'])assert.throws(()=>validateAction({kind}));
 let executions=0;const c=new DashboardController({prepare:async()=>({id:'ticket',expiresAt:new Date(Date.now()+60000).toISOString()}),execute:async()=>{executions++;}});
 await c.prepare({kind:'feature',featureId:'dice',enabled:false});await assert.rejects(c.confirm(false));c.cancel();await assert.rejects(c.confirm(true));assert.equal(executions,0);
});
test('cross-origin APIs are refused and operation errors are not retried',async()=>{
 assert.throws(()=>new HttpAdapter('https://other.test',{origin:'http://testserver'}));let calls=0;
 const a=new HttpAdapter('/api/dashboard',{origin:'http://testserver',fetcher:async()=>{calls++;return{ok:false,status:409,json:async()=>({detail:'expired'})};}});
 await assert.rejects(a.execute('ticket',{kind:'presence',value:'idle'}),/expired/);assert.equal(calls,1);
});
test('filters search level, module, text and context',()=>{
 const logs=[{level:'WARN',module:'gateway',message:'retry',context:{code:503}},{level:'INFO',module:'dice',message:'rolled',context:{}}];
 assert.equal(filterLogs(logs,{query:'503',level:'ISSUES'}).length,1);assert.equal(filterLogs(logs,{module:'dice'}).length,1);
});
