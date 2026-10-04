"""実main.pyの受付・スケジュールに設定が反映されることを、外部送信なしで検証する。"""
import os
from pathlib import Path
import subprocess
import sys
import textwrap


def test_main_dispatch_and_scheduled_notification_obey_feature_switches(tmp_path):
    script = textwrap.dedent('''
        import asyncio, sys, types
        calls = []
        def module(name):
            m = types.ModuleType(name)
            sys.modules[name] = m
            return m
        async def handler(name, *args):
            calls.append(name)
        iidx = module('feature.iidx')
        iidx.handle_iidx_practice_music = lambda *a: handler('iidx', *a)
        iidx.handle_dp_level = lambda *a: handler('dp_level', *a)
        tech = module('feature.tech')
        tech.fetch_trending_qiita = lambda: calls.append('tech_trend') or 'articles'
        dice = module('feature.dice_roll')
        dice.handle_dice = lambda *a: handler('dice', *a)
        meal = module('feature.meal_analyze')
        meal.handle_meal_analyze = lambda *a: handler('meal_analyze', *a)
        notion = module('feature.iidx_notion')
        notion.__path__ = []
        result = module('feature.iidx_notion.result_analyze')
        result.handle_sran_result = lambda *a: handler('result_analyze', *a)
        import main
        main.os.environ['DEBUG_MODE'] = '1'
        class Message:
            author = types.SimpleNamespace(bot=False)
            def __init__(self, content, channel_id, attachments):
                self.content = content
                self.attachments = attachments
                self.channel = types.SimpleNamespace(id=channel_id, send=lambda text: handler('sent',text))
        async def check():
            specs = [
                ('iidx','/iidx 12 3',main.cfg.DEBUG_CHANNNEL_ID,[]),
                ('dp_level','/dp_level test',main.cfg.DEBUG_CHANNNEL_ID,[]),
                ('dice','/dice 1 100',main.cfg.DEBUG_CHANNNEL_ID,[]),
                ('tech_trend','/tech_trend',main.cfg.DEBUG_CHANNNEL_ID,[]),
                ('meal_analyze','',main.cfg.DEBUG_CHANNNEL_ID,[object()]),
                ('result_analyze','',main.cfg.SRAN_RESULT_CHANNNEL_ID,[object()]),
            ]
            for feature, content, channel, attachments in specs:
                message = Message(content,channel,attachments)
                main.dashboard_runtime.store.set_setting('feature:'+feature,False)
                calls.clear()
                await main.on_message(message)
                assert feature not in calls, (feature,calls)
                main.dashboard_runtime.store.set_setting('feature:'+feature,True)
                await main.on_message(message)
                assert feature in calls, (feature,calls)
            calls.clear()
            main.dashboard_runtime.store.set_setting('feature:tech_trend',False)
            await main.scheduled_tech_trend_task.coro()
            assert 'tech_trend' not in calls
            # 管理者指定のstatusを定期アクティビティ更新でも維持する。
            main.dashboard_runtime.store.set_setting('presence','idle')
            async def presence(client,status):
                assert str(status)=='idle'
                return 'updated-activity'
            main.bot_status.set_presence=presence
            await main.update_presence.coro()
            assert main.dashboard_runtime.activity=='updated-activity'
            await main.client.close()
        asyncio.run(check())
    ''')
    env = dict(os.environ, DASHBOARD_DB_PATH=str(tmp_path/'main.sqlite3'))
    result = subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parent.parent,env=env,capture_output=True,text=True,timeout=15)
    assert result.returncode == 0, result.stderr
