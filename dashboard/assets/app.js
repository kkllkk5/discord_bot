import {HttpAdapter} from './adapter.js';
import {DashboardController,ACTIONS,filterLogs,actionDescription} from './controller.js';
const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon=name=>`<svg aria-hidden="true"><use href="#icon-${esc(name)}"/></svg>`;
const time=value=>new Date(value).toLocaleTimeString('ja-JP',{timeZone:'Asia/Tokyo',hour12:false});
const dateTime=value=>new Date(value).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo',hour12:false});
const adapter=new HttpAdapter('/api/dashboard');
const controller=new DashboardController(adapter);
let snapshot=null,displayLogs=[],level='ALL',paused=false,connected=false,polling=false,selectedLog=null,toastTimer=null,presenceDraft=null;
function toast(message,error=false){const box=$('toast');clearTimeout(toastTimer);box.classList.toggle('error',error);box.querySelector('span').textContent=message;box.hidden=false;toastTimer=setTimeout(()=>{box.hidden=true;},4500);}
function showDialog(id){if(!$(`${id}`).open) $(id).showModal();}
function closeDialog(id){if(id==='confirm-dialog'){if(controller.busy)return;controller.cancel();}$(id).close();renderControls();}
function filters(){return {level,module:$('module-filter').value,query:$('log-search').value};}
function renderLogs(){
  const list=filterLogs(displayLogs,filters());
  const viewport=$('log-viewport');const oldScroll=viewport.scrollTop;
  $('log-rows').innerHTML=list.map(log=>`<button class="log-row ${esc(log.level)}" data-log="${esc(log.id)}" aria-label="${esc(log.level+' '+log.message+' 詳細')}" title="詳細を表示"><time datetime="${esc(log.timestamp)}">${esc(time(log.timestamp))}</time><span class="log-level ${esc(log.level)}">${esc(log.level)}</span><span class="log-event"><span class="log-module">${esc(log.module)}</span><span class="log-message">${esc(log.message)}</span></span>${icon('chevron')}</button>`).join('');
  $('logs-empty').hidden=list.length>0;
  for(const name of ['ALL','INFO','WARN','ERROR']) $('count-'+name.toLowerCase()).textContent=name==='ALL'?displayLogs.length:displayLogs.filter(l=>l.level===name).length;
  for(const tab of document.querySelectorAll('[data-level]')){const selected=tab.dataset.level===level;tab.classList.toggle('selected',selected);tab.setAttribute('aria-pressed',String(selected));}
  const follow=$('follow-logs').checked&&!paused;
  if(follow) viewport.scrollTop=viewport.scrollHeight;else viewport.scrollTop=oldScroll;
  $('log-summary').textContent=`${list.length} / ${displayLogs.length} 件 · ${paused?'表示を一時停止':'新しいログが下に追加されます'}`;
  $('nav-issue-count').textContent=displayLogs.filter(l=>['WARN','ERROR'].includes(l.level)).length;
}
function renderControls(){
  const locked=!connected||controller.busy||!!controller.pending||snapshot?.controlsEnabled!==true;
  const online=snapshot?.bot.status==='online';
  $('presence').disabled=locked||!online;
  $('apply-presence').disabled=locked||!online||$('presence').value===snapshot?.bot.presence;
  for(const toggle of document.querySelectorAll('[data-feature]')) toggle.disabled=locked;
}
function render(){
  if(!snapshot)return;
  const bot=snapshot.bot;const online=bot.status==='online';
  $('metric-status').innerHTML=`<span class="status-value ${online?'':'offline'}">${online?'Online':'Offline'}</span>`;
  $('metric-status-note').textContent=online?`${bot.guilds} サーバーに接続中`:'実Botの更新を待機中';
  $('metric-latency').textContent=online&&bot.latencyMs!=null?bot.latencyMs:'—';
  $('metric-latency-note').textContent=online?'Gatewayの応答時間':'Gatewayへの接続なし';
  const elapsed=online?Math.max(0,Math.floor((Date.now()-Date.parse(bot.startedAt))/1000)):0;
  $('metric-uptime').textContent=online?`${Math.floor(elapsed/3600)}h ${String(Math.floor(elapsed%3600/60)).padStart(2,'0')}m`:'—';
  $('metric-started').textContent=bot.startedAt?`起動 ${time(bot.startedAt)} JST`:'起動時刻 —';
  const enabled=snapshot.features.filter(f=>f.enabled).length;
  $('metric-features').textContent=enabled;$('metric-feature-total').textContent=`/ ${snapshot.features.length}`;$('features-total').textContent=`${enabled} / ${snapshot.features.length} 有効`;
  $('bot-pill').textContent=online?'接続中':'未接続';$('bot-pill').classList.toggle('offline',!online);
  $('bot-avatar-dot').style.background=online?'var(--mint)':'#77858b';
  $('bot-name').textContent=bot.name;$('bot-guilds').textContent=online?`${bot.guilds} サーバー · Gateway接続中`:'実Botの状態更新を待機中';
  $('runtime-note').textContent=online?'機能とプレゼンスの変更を実Botに反映します。':'Botが未接続です。main.pyの起動と共有DBの設定を確認してください。';
  if(presenceDraft===bot.presence)presenceDraft=null;
  $('presence').value=presenceDraft??bot.presence;
  $('feature-list').innerHTML=snapshot.features.map(f=>`<div class="feature-row"><span class="feature-icon">${icon(f.icon||'grid')}</span><div class="feature-copy"><strong>${esc(f.name)}</strong><small>${esc(f.description)}</small></div><button class="toggle" role="switch" aria-checked="${Boolean(f.enabled)}" aria-label="${esc(f.name)}を${f.enabled?'無効':'有効'}にする" title="${f.enabled?'無効':'有効'}にする（確認あり）" data-feature="${esc(f.id)}"></button></div>`).join('');
  if(snapshot.audit.length){$('audit-list').innerHTML=`<div class="audit-list-scroll">${snapshot.audit.map(a=>`<div class="audit-row">${icon(a.result==='成功'?'check':'alert')}<time datetime="${esc(a.timestamp)}">${esc(time(a.timestamp))}</time><span class="audit-label">${esc(a.label)}</span><span class="audit-actor">${esc(a.actor)}</span><span class="audit-result">${esc(a.result)}</span></div>`).join('')}</div>`;}
  else $('audit-list').innerHTML=`<div class="audit-empty">${icon('shield')}<span>まだ管理操作はありません。確認して実行した操作がここに記録されます。</span></div>`;
  $('log-dot').style.background=connected?'#77b596':'#bf7b7b';
  renderControls();renderLogs();
}
async function refresh({notify=false}={}){
  if(polling)return;polling=true;$('refresh').disabled=true;
  try {snapshot=await adapter.snapshot();connected=true;if(!paused)displayLogs=snapshot.logs;$('api-error').hidden=true;$('last-updated').textContent=`最終更新 ${time(new Date())} JST`;render();if(notify)toast('最新の状態に更新しました');}
  catch(error){connected=false;if(error.status===401||error.status===503){$('login-error').textContent=error.status===503?error.message:'';showDialog('login-dialog');}$('api-error').textContent=`状態を取得できませんでした：${error.message} 更新ボタンで再試行できます。`;$('api-error').hidden=false;renderControls();}
  finally{polling=false;$('refresh').disabled=false;}
}
async function requestAction(action){
  if(!snapshot||!connected)return;
  try{const preparing=controller.prepare(action);renderControls();const ticket=await preparing;
    $('confirm-title').textContent=ACTIONS[action.kind];$('confirm-description').textContent=actionDescription(action,snapshot);
    $('confirm-target').textContent=ticket.target;$('confirm-mode').textContent='実際のBotと接続先システムに変更を反映します。';
    $('accept-action').checked=false;$('confirm-action').disabled=true;$('confirm-action').textContent='確認して実行';
    $('expiry-note').textContent='確認は60秒間有効です。キャンセル時は実行されません。';showDialog('confirm-dialog');renderControls();
  }catch(error){toast(error.message,true);renderControls();}
}
$('confirm-action').addEventListener('click',async()=>{
  if(!$('accept-action').checked)return;
  $('confirm-action').disabled=true;$('confirm-action').textContent='実行中…';
  try{const kind=controller.pending?.action.kind;const executing=controller.confirm(true);renderControls();await executing;if(kind==='presence')presenceDraft=null;$('confirm-dialog').close();await refresh();toast('実Botへの操作適用を確認しました');}
  catch(error){$('confirm-dialog').close();await refresh();toast(error.message,true);}
  finally{$('confirm-action').textContent='確認して実行';renderControls();}
});
$('accept-action').addEventListener('change',()=>{$('confirm-action').disabled=!$('accept-action').checked||controller.busy||!controller.pending||Date.parse(controller.pending.expiresAt)<=Date.now();});
$('confirm-dialog').addEventListener('cancel',event=>{if(controller.busy){event.preventDefault();return;}controller.cancel();renderControls();});
for(const button of document.querySelectorAll('[data-close]'))button.addEventListener('click',()=>closeDialog(button.dataset.close));
for(const id of ['guide-dialog','detail-dialog']) $(id).addEventListener('click',event=>{if(event.target===$(id)){const r=$(id).getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)$(id).close();}});
$('presence').addEventListener('change',()=>{presenceDraft=$('presence').value;renderControls();});$('apply-presence').addEventListener('click',()=>requestAction({kind:'presence',value:$('presence').value}));
$('feature-list').addEventListener('click',event=>{const toggle=event.target.closest('[data-feature]');if(!toggle||toggle.disabled)return;const f=snapshot.features.find(f=>f.id===toggle.dataset.feature);if(f)requestAction({kind:'feature',featureId:f.id,enabled:!f.enabled});});
$('refresh').addEventListener('click',()=>refresh({notify:true}));
$('log-search').addEventListener('input',renderLogs);$('module-filter').addEventListener('change',renderLogs);$('follow-logs').addEventListener('change',renderLogs);
for(const tab of document.querySelectorAll('[data-level]'))tab.addEventListener('click',()=>{level=tab.dataset.level;renderLogs();});
$('pause-logs').addEventListener('click',()=>{paused=!paused;if(!paused&&snapshot)displayLogs=snapshot.logs;$('pause-logs').innerHTML=icon(paused?'play':'pause');$('pause-logs').setAttribute('aria-label',paused?'ログ表示を再開':'ログ表示を一時停止');$('pause-logs').title=paused?'ログ表示を再開':'ログ表示を一時停止';$('live-tag').classList.toggle('paused',paused);$('live-tag').innerHTML=`<span></span>${paused?'PAUSED':'LIVE'}`;renderLogs();});
function navigate(section){for(const item of document.querySelectorAll('.nav-item'))item.classList.toggle('active',item.id===`nav-${section}`);if(section==='overview')window.scrollTo({top:0,behavior:'smooth'});else{$('log-panel').scrollIntoView({behavior:'smooth',block:'start'});level=section==='issues'?'ISSUES':'ALL';$('module-filter').value='ALL';$('log-search').value='';renderLogs();}}
$('nav-overview').addEventListener('click',()=>navigate('overview'));$('nav-logs').addEventListener('click',()=>navigate('logs'));$('nav-issues').addEventListener('click',()=>navigate('issues'));
for(const id of ['nav-guide','banner-guide'])$(id).addEventListener('click',()=>showDialog('guide-dialog'));
$('log-rows').addEventListener('click',event=>{const row=event.target.closest('[data-log]');if(!row)return;selectedLog=displayLogs.find(log=>log.id===row.dataset.log);if(!selectedLog)return;$('log-detail').innerHTML=`<div class="detail-meta"><span class="log-level ${esc(selectedLog.level)}">${esc(selectedLog.level)}</span><span>${esc(selectedLog.module)}</span><time>${esc(dateTime(selectedLog.timestamp))} JST</time></div><p class="detail-message">${esc(selectedLog.message)}</p><pre class="json-block">${esc(JSON.stringify(selectedLog,null,2))}</pre>`;showDialog('detail-dialog');});
$('copy-log').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(JSON.stringify(selectedLog,null,2));toast('ログのJSONをコピーしました');}catch{toast('コピーできませんでした。詳細欄のJSONを選択してコピーしてください。',true);}});
$('download-logs').addEventListener('click',()=>{const logs=filterLogs(displayLogs,filters());const blob=new Blob([JSON.stringify({exportedAt:new Date().toISOString(),mode:'http',filters:filters(),logs},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`discord-bot-logs-${new Date().toISOString().slice(0,10)}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast(`${logs.length}件のログを保存しました`);});
$('login-dialog').addEventListener('cancel',event=>event.preventDefault());
$('login-form').addEventListener('submit',async event=>{
  event.preventDefault();$('login-submit').disabled=true;$('login-error').textContent='';
  try{await adapter.login($('login-token').value);$('login-token').value='';$('login-dialog').close();await refresh();}
  catch(error){$('login-token').value='';$('login-error').textContent=error.message;}
  finally{$('login-submit').disabled=false;}
});
$('logout').addEventListener('click',async()=>{
  try{await adapter.logout();snapshot=null;displayLogs=[];connected=false;controller.cancel();$('feature-list').innerHTML='';$('audit-list').innerHTML='';$('metric-status').textContent='—';$('metric-latency').textContent='—';$('metric-uptime').textContent='—';$('metric-features').textContent='—';renderLogs();renderControls();showDialog('login-dialog');}
  catch(error){toast(error.message,true);}
});
document.addEventListener('keydown',event=>{const editing=['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName);if(event.key==='/'&&!editing&&!document.querySelector('dialog[open]')){event.preventDefault();$('log-search').focus();}});
await refresh();
setInterval(()=>{if(!$('login-dialog').open)refresh();},5000);
setInterval(()=>{if(controller.pending&&$('confirm-dialog').open){const remaining=Math.max(0,Math.ceil((Date.parse(controller.pending.expiresAt)-Date.now())/1000));$('expiry-note').textContent=remaining?`確認の有効期限：残り${remaining}秒`:'確認の有効期限が切れました。キャンセルして再操作してください。';if(!remaining)$('confirm-action').disabled=true;}},1000);
