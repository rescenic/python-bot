"""Plugin Backup and Restore"""
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
import json
from datetime import datetime
from typing import Any, ClassVar, MutableMapping, Optional

from aiopath import AsyncPath

from anjani import command, filters, plugin


class Backups(plugin.Plugin):
    name: ClassVar[str] = "Backups"
    helpable: ClassVar[bool] = True

    @command.filters(filters.admin_only)
    async def cmd_backup(self, ctx: command.Context) -> Optional[str]:
        """Backup chat data from file"""
        chat = ctx.msg.chat
        data = {"chat_id": chat.id}
        file = AsyncPath(f"{chat.title}-backup.anjani")

        await ctx.respond(await self.text(chat.id, "backup-progress"))

        tasks = await self.bot.dispatch_event("plugin_backup", chat.id, get_tasks=True)
        if not tasks:
            return await self.text(chat.id, "backup-null")

        task: asyncio.Task[MutableMapping[str, Any]]
        for task in tasks:
            # Make sure all plugin backup are done
            if not task.done():
                await task

            # skip adding to data if result is empty map
            result = task.result()
            if not result:
                continue

            data.update(result)

        if len(data.keys()) <= 1:
            return await self.text(chat.id, "backup-null")

        # Create the file and write the data
        await file.touch()
        await file.write_text(json.dumps(data, indent=2))

        saved = ""
        del data["chat_id"]
        for key in data:
            saved += f"\n× `{key}`"

        date = datetime.now().strftime("%H:%M - %d/%b/%Y")
        await asyncio.gather(
            ctx.msg.reply_document(
                str(file),
                caption=await self.text(chat.id, "backup-doc", chat.title, chat.id, date, saved),
            ),
            ctx.response.delete(),
            file.unlink(),
        )
        return None

    @command.filters(filters.admin_only)
    async def cmd_restore(self, ctx: command.Context) -> Optional[str]:
        """Restore data to a file"""
        chat = ctx.msg.chat
        reply_msg = ctx.msg.reply_to_message

        if not reply_msg or (reply_msg and not reply_msg.document):
            return await self.text(chat.id, "no-backup-file")

        await ctx.respond(await self.text(chat.id, "restore-progress"))

        file = AsyncPath(await ctx.msg.reply_to_message.download())
        data: MutableMapping[str, Any] = json.loads(await file.read_text())

        try:  # also check if the file isn't a valid backup file
            if data["chat_id"] != chat.id:
                return await self.text(chat.id, "backup-id-invalid")
        except KeyError:
            return await self.text(chat.id, "invalid-backup-file")

        if len(data.keys()) == 1:
            return await self.text(chat.id, "backup-data-null")

        await self.bot.dispatch_event("plugin_restore", chat.id, data)
        await asyncio.gather(ctx.respond(await self.text(chat.id, "backup-done")), file.unlink())
        return None
