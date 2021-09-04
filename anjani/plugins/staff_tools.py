"""staff's commands"""
# Copyright (C) 2020 - 2021  UserbotIndo Team, <https://github.com/userbotindo.git>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import asyncio
from io import BytesIO
from typing import ClassVar, Optional, Set

from aiopath import AsyncPath
from pyrogram.errors.exceptions.bad_request_400 import (
    ChannelInvalid,
    PeerIdInvalid,
    UserNotParticipant,
)

from anjani import command, filters, plugin, util


class Staff(plugin.Plugin):
    name: ClassVar[str] = "Staff Tools"

    db: util.db.AsyncCollection

    async def on_load(self) -> None:
        self.db = self.bot.db.get_collection("CHATS")

    @command.filters(filters.owner_only)
    async def cmd_broadcast(self, ctx: command.Context) -> Optional[str]:
        """Broadcast a message to all chats"""
        if not ctx.input:
            return "Give me a message to send."

        await ctx.respond("Sending broadcast...")

        text = ctx.input + "\n\n*This is a broadcast message."
        tasks: Set[asyncio.Task] = set()
        async for chat in self.db.find({}):
            if len(tasks) % 25 == 0:
                # sleep every 25 msg tasks to prevent flood limit.
                await asyncio.sleep(1)

            task = self.bot.loop.create_task(self.bot.client.send_message(chat["chat_id"], text))
            tasks.add(task)

        failed = 0
        sent = 0
        done, _ = await asyncio.wait(tasks)
        for fut in done:
            try:
                fut.result()
            except (PeerIdInvalid, ChannelInvalid):
                failed += 1
            else:
                sent += 1

        return (
            "Broadcast complete!\n"
            f"{sent} groups succeed, {failed} groups failed to receive the message"
        )

    @command.filters(filters.staff_only)
    async def cmd_leavechat(self, ctx: command.Context) -> str:
        """leave the given chat_id"""
        if not ctx.args or ctx.input:
            return "Give me the chat id!"

        try:
            await self.bot.client.leave_chat(ctx.args[0])
        except (PeerIdInvalid, UserNotParticipant):
            return "I'm not a member on that group"
        else:
            return "I left the group"

    @command.filters(filters.staff_only)
    async def cmd_chatlist(self, ctx: command.Context) -> None:
        """Send file of chat's I'm in"""
        chatfile = "List of chats.\n"
        async for chat in self.db.find({}):
            chatfile += "{} - ({})\n".format(chat["chat_name"], chat["chat_id"])

        with BytesIO(str.encode(chatfile)) as output:
            output.name = "chatlist.txt"
            await ctx.msg.reply_document(
                document=output,
                caption="Here is the list of chats in my database.",
            )

    @command.filters(filters.staff_only)
    async def cmd_logs(self, ctx: command.Context) -> None:
        """Send bot log"""
        file = AsyncPath("Anjani.log")
        if ctx.message.chat.type != "private":
            await ctx.respond("I've send the log on PM's")

        await self.bot.client.send_document(
            ctx.author.id,
            str(file),
            caption="**Bot Logs**",
            force_document=True,
        )
