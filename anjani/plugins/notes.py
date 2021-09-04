"""Notes"""
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
from typing import Any, Callable, ClassVar, Coroutine, MutableMapping, Optional

from pyrogram import filters
from pyrogram.types import Message

from anjani import command, listener, plugin, util
from anjani.filters import admin_only
from anjani.util.tg import Types, build_button, get_message_info, revert_button


class Notes(plugin.Plugin):
    name: ClassVar[str] = "Notes"
    helpable: ClassVar[bool] = True

    db: util.db.AsyncCollection
    SEND: MutableMapping[int, Callable[..., Coroutine[Any, Any, Optional[Message]]]]

    async def on_load(self):
        self.db = self.bot.db.get_collection("NOTES")
        self.SEND = {
            Types.TEXT.value: self.bot.client.send_message,
            Types.BUTTON_TEXT.value: self.bot.client.send_message,
            Types.DOCUMENT.value: self.bot.client.send_document,
            Types.PHOTO.value: self.bot.client.send_photo,
            Types.VIDEO.value: self.bot.client.send_video,
            Types.STICKER.value: self.bot.client.send_sticker,
            Types.AUDIO.value: self.bot.client.send_audio,
            Types.VOICE.value: self.bot.client.send_voice,
            Types.VIDEO_NOTE.value: self.bot.client.send_video_note,
            Types.ANIMATION.value: self.bot.client.send_animation,
        }

    async def on_chat_migrate(self, message: Message) -> None:
        new_chat = message.chat.id
        old_chat = message.migrate_from_chat_id

        await self.db.update_one(
            {"chat_id": old_chat},
            {"$set": {"chat_id": new_chat}},
        )

    async def on_plugin_backup(self, chat_id: int) -> MutableMapping[str, Any]:
        notes = await self.db.find_one({"chat_id": chat_id}, {"_id": False})
        if not notes:
            return {}

        return {self.name: notes}

    async def on_plugin_restore(self, chat_id: int, data: MutableMapping[str, Any]) -> None:
        await self.db.update_one({"chat_id": chat_id}, {"$set": data[self.name]}, upsert=True)

    @listener.filters(filters.regex(r"^#[^\s]+"))
    async def on_message(self, message: Message) -> None:
        """Notes hashtag trigger."""
        entity = message.entities
        if not entity or entity and entity[0].type != "hashtag":
            return

        invoker = message.text[1 : entity[0].length]
        await self.get_note(message, invoker)

    async def get_note(self, message: Message, name: str, noformat: bool = False) -> None:
        """Get note data and send based on types."""
        chat = message.chat
        reply_to = message.message_id

        data = await self.db.find_one({"chat_id": chat.id})
        if not data or not data.get("notes"):
            return

        note: MutableMapping[str, Any]
        try:
            note = data["notes"][name]
        except KeyError:
            return

        button = note.get("button", None)
        if noformat:
            parse_mode = None
            btn_text = "\n\n"
            if button:
                btn_text += revert_button(button)
            keyb = None
        else:
            parse_mode = "markdown"
            btn_text = ""
            if button:
                keyb = build_button(button)
            else:
                keyb = button

        types: int = note["type"]
        if types in {Types.TEXT, Types.BUTTON_TEXT}:
            await self.SEND[types](
                chat.id,
                note["text"] + btn_text,
                disable_web_page_preview=True,
                reply_to_message_id=reply_to,
                reply_markup=keyb,
                parse_mode=parse_mode,
            )
        elif types == Types.STICKER:
            await self.SEND[types](
                chat.id,
                note["content"],
                reply_to_message_id=reply_to,
            )
        else:
            await self.SEND[types](
                chat.id,
                str(note["content"]),
                caption=note["text"] + btn_text,
                reply_to_message_id=reply_to,
                reply_markup=keyb,
                parse_mode=parse_mode,
            )

    async def cmd_get(self, ctx: command.Context) -> None:
        """Notes command trigger."""
        if not ctx.input:
            return

        if len(ctx.args) >= 2 and ctx.args[1].lower() == "noformat":
            await self.get_note(ctx.msg, ctx.args[0], noformat=True)
        else:
            await self.get_note(ctx.msg, ctx.args[0])

    @command.filters(admin_only)
    async def cmd_save(self, ctx: command.Context) -> str:
        """Save notes."""
        chat = ctx.chat
        if len(ctx.args) < 2 and not ctx.msg.reply_to_message:
            return await self.text(chat.id, "notes-invalid-args")

        name = ctx.args[0]
        text, types, content, buttons = get_message_info(ctx.msg)
        ret = await asyncio.gather(
            self.db.update_one(
                {"chat_id": chat.id},
                {
                    "$set": {
                        "chat_name": chat.title,
                        f"notes.{name}": {
                            "text": text if text else f"__{name}__",
                            "type": types,
                            "content": content,
                            "button": buttons,
                        },
                    }
                },
                upsert=True,
            ),
            self.text(chat.id, "note-saved", name),
        )
        return ret[1]

    async def cmd_notes(self, ctx: command.Context) -> str:
        """View chat notes."""
        chat = ctx.chat

        data = await self.db.find_one({"chat_id": chat.id})
        if not data or not data.get("notes"):
            return await self.text(chat.id, "no-notes")

        notes = await self.text(chat.id, "note-list", chat.title)
        for key in data["notes"].keys():
            notes += f"× `{key}`\n"
        return notes

    @command.filters(admin_only, aliases=["clear"])
    async def cmd_delnote(self, ctx: command.Context) -> str:
        """Delete chat note."""
        chat = ctx.chat
        if not ctx.input:
            return await self.text(chat.id, "notes-del-noargs")

        name = ctx.input

        data = await self.db.find_one({"chat_id": chat.id})
        if not data or not data.get("notes"):
            return await self.text(chat.id, "no-notes")

        notes: MutableMapping[str, Any] = data["notes"]
        try:
            notes[name]
        except KeyError:
            return await self.text(chat.id, "notes-not-exist")

        ret = await asyncio.gather(
            self.db.update_one({"chat_id": chat.id}, {"$unset": {f"notes.{name}": ""}}),
            self.text(chat.id, "notes-deleted", name),
        )
        return ret[1]
