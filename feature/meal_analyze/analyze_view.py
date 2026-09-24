import asyncio
from typing import Optional

import discord

from feature import constants


class AnalyzeView(discord.ui.View):
    def __init__(self, owner_id, IDOLS):
        super().__init__(timeout=300)
        self.result = None
        self.event = asyncio.Event()
        self.owner_id = owner_id

        for label, row, analyzer_id, emoji, style in IDOLS:
            button = discord.ui.Button(
                label=label,
                emoji=emoji,
                style=style,
                row=row,
            )

            async def callback(interaction, analyzer_id=analyzer_id, button=button):
                # メッセージの送信対象のユーザーしかボタンを押せないようにする
                if interaction.user.id != self.owner_id:
                    return

                self.result = analyzer_id

                # ボタンを押した後,全ボタンを無効化
                button.style = discord.ButtonStyle.success
                for item in self.children:
                    if isinstance(item, discord.ui.Button):
                        item.disabled = True

                await interaction.response.edit_message(content="解析中...", view=self)

                # 待機している処理を再開
                self.event.set()
                self.stop()

            button.callback = callback
            self.add_item(button)

    # タイムアウト時の処理
    async def on_timeout(self):
        # ボタンを全部無効化
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        self.result = constants.ANALYZER_ID_CANCELLED
        self.event.set()
        self.stop()
