export const ACTIONS = Object.freeze({ presence: 'プレゼンスを変更', feature: '機能の状態を変更' });
export function validateAction(action) {
  if (!action || typeof action.kind !== 'string' || !Object.hasOwn(ACTIONS, action.kind)) throw new Error('未対応の操作です。');
  if (action.kind === 'presence' && !['online','idle','dnd'].includes(action.value)) throw new Error('プレゼンスが不正です。');
  if (action.kind === 'feature' && (!['meal_analyze','iidx','dp_level','result_analyze','tech_trend','dice'].includes(action.featureId) || typeof action.enabled !== 'boolean')) throw new Error('機能の指定が不正です。');
  const out = {kind: action.kind};
  if(action.kind === 'presence') out.value = action.value;
  if(action.kind === 'feature') {out.featureId = action.featureId; out.enabled = action.enabled;}
  return out;
}
export function filterLogs(logs, {level = 'ALL', module = 'ALL', query = ''} = {}) {
  const q = query.trim().toLocaleLowerCase();
  return logs.filter(log => (level === 'ALL' || (level === 'ISSUES' ? ['WARN','ERROR'].includes(log.level) : log.level === level)) && (module === 'ALL' || log.module === module) && (!q || `${log.message} ${log.module} ${JSON.stringify(log.context || {})}`.toLocaleLowerCase().includes(q)));
}
export function actionDescription(action, snapshot) {
  validateAction(action);
  if(action.kind === 'presence') return `Discordでの表示を「${{online:'オンライン',idle:'退席中',dnd:'取り込み中'}[action.value]}」に変更します。`;
  const name = snapshot.features.find(f => f.id === action.featureId)?.name || action.featureId;
  return `「${name}」を${action.enabled ? '有効' : '無効'}にします。${action.enabled ? '対象機能の処理が再開します。' : '対象機能の新規処理が停止します。実行中の処理は継続します。'}`;
}
// All mutations pass through this state machine. Preparing never changes Bot state.
export class DashboardController {
  constructor(adapter) {this.adapter = adapter; this.pending = null; this.busy = false;}
  async prepare(action) {
    if(this.busy || this.pending) throw new Error('確認中の操作を完了またはキャンセルしてください。');
    this.busy = true;
    try { const safe = validateAction(action); const ticket = await this.adapter.prepare(safe); this.pending = {...ticket, action:safe}; return this.pending; }
    finally {this.busy = false;}
  }
  cancel() {if(!this.busy) this.pending = null;}
  async confirm(accepted) {
    if(accepted !== true) throw new Error('明示的な確認が必要です。');
    if(this.busy || !this.pending) throw new Error('確認する操作がありません。');
    const ticket = this.pending;
    if(Date.parse(ticket.expiresAt) <= Date.now()) {this.pending = null; throw new Error('確認の有効期限が切れました。もう一度操作してください。');}
    this.busy = true;
    try {return await this.adapter.execute(ticket.id, ticket.action);}
    finally {this.pending = null; this.busy = false;}
  }
}
