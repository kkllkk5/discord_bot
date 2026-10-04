import {validateAction} from './controller.js';
export class HttpAdapter {
  constructor(base='/api/dashboard',{fetcher=globalThis.fetch,origin=globalThis.location?.origin}={}) {
    const url=new URL(base,origin);
    if(url.origin!==origin||!base.startsWith('/')||base.startsWith('//')) throw new Error('同一オリジンのAPIだけに接続できます。');
    this.base=base.replace(/\/$/,'');this.fetcher=fetcher;
  }
  // 読み取りと確認済み操作のAPIを呼ぶ。失敗・タイムアウト時は自動再試行しない。
  async request(path,method='GET',body){
    const response=await this.fetcher(this.base+path,{method,credentials:'same-origin',cache:'no-store',headers:body?{'Content-Type':'application/json'}:{},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(10000)});
    const data=await response.json();
    if(!response.ok){const error=new Error(typeof data.detail==='string'?data.detail:`APIエラー (${response.status})`);error.status=response.status;throw error;}
    return data;
  }
  snapshot(){return this.request('/snapshot');}
  prepare(action){return this.request('/actions/prepare','POST',{action:validateAction(action)});}
  execute(id,action){return this.request('/actions/execute','POST',{ticketId:id,action:validateAction(action),confirmed:true});}
  login(token){return this.request('/session','POST',{token});}
  logout(){return this.request('/logout','POST',{});}
}
