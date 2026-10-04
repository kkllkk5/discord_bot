// Lightweight DOM harness: exercise the real app event handlers without a browser.
// It validates behavior and wiring; it is not a layout or browser compatibility test.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
class Classes {
 constructor(value=''){this.items=new Set(value.split(/\s+/).filter(Boolean));}
 toggle(name,force){if(force===undefined)force=!this.items.has(name);if(force)this.items.add(name);else this.items.delete(name);return force;}
 remove(name){this.items.delete(name);}
}
class Element {
 constructor(tag,attrs={}){this.tagName=tag.toUpperCase();this.id=attrs.id;this.attrs=attrs;this.classList=new Classes(attrs.class||'');this.dataset={};for(const [k,v] of Object.entries(attrs))if(k.startsWith('data-'))this.dataset[k.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=v;this.hidden=Object.hasOwn(attrs,'hidden');this.disabled=Object.hasOwn(attrs,'disabled');this.checked=Object.hasOwn(attrs,'checked');this.value='';this.textContent='';this.style={};this.open=false;this.events={};this.scrollTop=0;this.scrollHeight=1000;this._html='';}
 set innerHTML(html){this._html=html;this.generated=parseElements(html);}
 get innerHTML(){return this._html;}
 setAttribute(key,value){this.attrs[key]=value;}
 addEventListener(name,fn){(this.events[name]??=[]).push(fn);}
 async dispatch(name,event={}){for(const fn of this.events[name]||[])await fn({target:this,preventDefault(){},...event});}
 async click(){if(!this.disabled)await this.dispatch('click');}
 querySelector(selector){if(selector==='span')return this.span??=new Element('span');return null;}
 closest(selector){const attr=selector.slice(1,-1);return Object.hasOwn(this.attrs,attr)?this:null;}
 showModal(){this.open=true;}
 close(){this.open=false;}
 scrollIntoView(){}
 focus(){document.activeElement=this;}
}
function parseElements(html){const out=[];for(const match of html.matchAll(/<([a-z][\w-]*)\b([^>]*?)>/gi)){const attrs={};for(const a of match[2].matchAll(/([\w-]+)(?:="([^"]*)")?/g))attrs[a[1]]=a[2]??'';out.push(new Element(match[1],attrs));}return out;}
function fakeDOM(html){const elements=parseElements(html);const ids=elements.filter(e=>e.id).map(e=>e.id);assert.equal(new Set(ids).size,ids.length,"Duplicate HTML IDs");const map=new Map(elements.filter(e=>e.id).map(e=>[e.id,e]));const all=()=>[...elements,...[...map.values()].flatMap(e=>e.generated||[])];const doc={activeElement:null,events:{},getElementById:id=>map.get(id),querySelectorAll(selector){if(selector==='.nav-item')return all().filter(e=>e.classList.items.has('nav-item'));if(selector.startsWith('[')){const attr=selector.slice(1,-1);return all().filter(e=>Object.hasOwn(e.attrs,attr));}return [];},querySelector:selector=>selector==='dialog[open]'?all().find(e=>e.tagName==='DIALOG'&&e.open):null,addEventListener:Element.prototype.addEventListener,createElement:tag=>new Element(tag)};map.get('module-filter').value='ALL';map.get('presence').value='online';map.get('follow-logs').checked=true;return doc;}
const settle=()=>new Promise(resolve=>setImmediate(resolve));
test('actual UI: authenticated API, prepare/cancel, explicit confirm, filters, log details and logout',async()=>{
 const html=await readFile(new URL('../index.html',import.meta.url),'utf8');
 assert.doesNotMatch(html,/start-bot|stop-bot|restart-bot|sample-tools/);
 const doc=fakeDOM(html);let authenticated=false;let executions=0;let prepared=null;
 const state={mode:'http',controlsEnabled:true,bot:{name:'discord_bot',status:'online',presence:'online',startedAt:new Date().toISOString(),latencyMs:42,guilds:2},features:[{id:'meal_analyze',name:'食事解析',description:'Gemini',icon:'spark',enabled:true},{id:'dice',name:'ダイス',description:'/dice',icon:'grid',enabled:true}],logs:[{id:'1',timestamp:new Date().toISOString(),level:'WARN',module:'gateway',message:'connection retry',context:{}}],audit:[]};
 const original={document:globalThis.document,window:globalThis.window,location:globalThis.location,fetch:globalThis.fetch,setInterval:globalThis.setInterval,setTimeout:globalThis.setTimeout,clearTimeout:globalThis.clearTimeout};
 globalThis.document=doc;globalThis.window={scrollTo(){}};globalThis.location={origin:'http://testserver'};globalThis.setInterval=()=>1;globalThis.setTimeout=()=>1;globalThis.clearTimeout=()=>{};
 globalThis.fetch=async(url,options)=>{
  const body=options.body?JSON.parse(options.body):null;
  const response=(data,status=200)=>({ok:status===200,status,json:async()=>data});
  if(url.endsWith('/session')){authenticated=true;assert.equal(body.token,'admin-token');return response({ok:true});}
  if(!authenticated)return response({detail:'login required'},401);
  if(url.endsWith('/snapshot'))return response(structuredClone(state));
  if(url.endsWith('/prepare')){prepared=body.action;return response({id:'ticket',expiresAt:new Date(Date.now()+60000).toISOString(),target:'discord_bot'});}
  if(url.endsWith('/execute')){assert.equal(body.confirmed,true);assert.deepEqual(body.action,prepared);executions++;if(prepared.kind==='feature')state.features.find(f=>f.id===prepared.featureId).enabled=prepared.enabled;else state.bot.presence=prepared.value;return response({ok:true});}
  if(url.endsWith('/logout')){authenticated=false;return response({ok:true});}
  throw Error(url);
 };
 try{
  await import('../assets/app.js?ui');const $=id=>doc.getElementById(id);
  assert.equal($('login-dialog').open,true);
  $('login-token').value='admin-token';await $('login-form').dispatch('submit');assert.equal($('login-token').value,'');assert.equal($('login-dialog').open,false);assert.match($('metric-status').innerHTML,/Online/);
  let toggle=doc.querySelectorAll('[data-feature]')[0];await $('feature-list').dispatch('click',{target:toggle});await settle();assert.equal($('confirm-dialog').open,true);assert.equal(executions,0);assert.equal($('confirm-action').disabled,true);
  await $('confirm-action').click();assert.equal(executions,0);
  const cancel=doc.querySelectorAll('[data-close]').find(e=>e.dataset.close==='confirm-dialog');await cancel.click();assert.equal(executions,0);
  toggle=doc.querySelectorAll('[data-feature]')[0];await $('feature-list').dispatch('click',{target:toggle});await settle();$('accept-action').checked=true;await $('accept-action').dispatch('change');await $('confirm-action').click();assert.equal(executions,1);assert.equal(state.features[0].enabled,false);
  $('presence').value='idle';await $('presence').dispatch('change');await $('apply-presence').click();$('accept-action').checked=true;await $('accept-action').dispatch('change');await $('confirm-action').click();assert.equal(state.bot.presence,'idle');
  $('log-search').value='notfound';await $('log-search').dispatch('input');assert.equal($('logs-empty').hidden,false);$('log-search').value='';await $('log-search').dispatch('input');
  const row=$('log-rows').generated.find(e=>e.dataset.log);await $('log-rows').dispatch('click',{target:row});assert.match($('log-detail').innerHTML,/connection retry/);$('detail-dialog').close();
  await $('logout').click();assert.equal($('login-dialog').open,true);assert.equal($('feature-list').innerHTML,'');assert.equal($('log-rows').innerHTML,'');
 }finally{for(const[key,value]of Object.entries(original)){if(value===undefined)delete globalThis[key];else globalThis[key]=value;}}
});
