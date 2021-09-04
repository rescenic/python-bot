from typing import Any, Callable, Coroutine

from pyrogram import Client
from pyrogram.filters import Filter
from pyrogram.types import Message

from anjani.util.tg import fetch_permissions, is_staff_or_admin
from anjani.util.types import CustomFilter

FilterFunc = Callable[[CustomFilter, Client, Message],
                      Coroutine[Any, Any, bool]]


def create(func: FilterFunc, name: str = None, **kwargs: Any) -> CustomFilter:
    return type(
        name or func.__name__ or "CustomAnjaniFilter",
        (CustomFilter,),
        {"__call__": func, **kwargs}
    )()


# { staff_only
def _staff_only(include_bot: bool = True) -> CustomFilter:

    async def func(flt: CustomFilter, _: Client, message: Message) -> bool:
        user = message.from_user
        return user.id in flt.anjani.staff

    return create(func, "staff_only", include_bot=include_bot)

staff_only = _staff_only()
# }


# { owner_only
def _owner_only(include_bot: bool = True) -> CustomFilter:

    async def func(flt: CustomFilter, _: Client, message: Message) -> bool:
        user = message.from_user
        return user.id == flt.anjani.owner

    return create(func, "owner_only", include_bot=include_bot)

owner_only = _owner_only()
# }


# { permission
async def _can_delete(_: Filter, client: Client, message: Message) -> bool:
    if message.chat.type == "private":
        return False

    bot, member = await fetch_permissions(client, message.chat.id,
                                          message.from_user.id)
    return bot.can_delete_messages and member.can_delete_messages


async def _can_change_info(_: Filter, client: Client, message: Message) -> bool:
    if message.chat.type == "private":
        return False

    bot, member = await fetch_permissions(client, message.chat.id,
                                          message.from_user.id)
    return bot.can_change_info and member.can_change_info


async def _can_invite(_: Filter, client: Client, message: Message) -> bool:
    if message.chat.type == "private":
        return False

    bot, member = await fetch_permissions(client, message.chat.id,
                                          message.from_user.id)
    return bot.can_invite_users and member.can_invite_users


async def _can_pin(_: Filter, client: Client, message: Message) -> bool:
    if message.chat.type == "private":
        return False

    bot, member = await fetch_permissions(client, message.chat.id,
                                          message.from_user.id)
    return bot.can_pin_messages and member.can_pin_messages


async def _can_promote(_: Filter, client: Client, message: Message) -> bool:
    if message.chat.type == "private":
        return False

    bot, member = await fetch_permissions(client, message.chat.id,
                                          message.from_user.id)
    return bot.can_promote_members and member.can_promote_members


async def _can_restrict(_: Filter, client: Client, message: Message) -> bool:
    if message.chat.type == "private":
        return False

    bot, member = await fetch_permissions(client, message.chat.id,
                                          message.from_user.id)
    return bot.can_restrict_members and member.can_restrict_members


can_delete = create(_can_delete, "can_delete")
can_change_info = create(_can_change_info, "can_change_info")
can_invite = create(_can_invite, "can_invite")
can_pin = create(_can_pin, "can_pin")
can_promote = create(_can_promote, "can_promote")
can_restrict = create(_can_restrict, "can_restrict")
# }


# { admin_only
def _admin_only(include_bot: bool = True) -> CustomFilter:

    async def func(flt: CustomFilter, client: Client, message: Message) -> bool:
        if message.chat.type == "private":
            return False

        user = message.from_user
        bot, member = await fetch_permissions(client, message.chat.id, user.id)
        return (
            bot.status == "administrator" and
            is_staff_or_admin(member, flt.anjani.staff)
        )

    return create(func, "admin_only", include_bot=include_bot)

admin_only = _admin_only()
# }
