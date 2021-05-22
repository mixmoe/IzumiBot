import re
from asyncio import get_running_loop
from collections import defaultdict
from enum import IntEnum, auto
from typing import DefaultDict, Optional, Set, Type

from nonebot.adapters.cqhttp import GroupMessageEvent, MessageEvent
from nonebot.matcher import Matcher
from nonebot.message import run_preprocessor
from nonebot.adapters import Bot, Event
from nonebot.typing import T_State

from .extractors import extract_text


@run_preprocessor
async def handle_cancellation(
    matcher: Matcher, bot: Bot, event: Event, state: T_State
) -> None:
    if not isinstance(event, MessageEvent):
        return
    text = extract_text(event.message)
    if _is_cancellation(text):
        await matcher.finish("好的")


def _is_cancellation(sentence: str) -> bool:
    for kw in ("算", "别", "不", "停", "取消"):
        if kw in sentence:
            # a keyword matches
            break
    else:
        # no keyword matches
        return False

    if re.match(r"^那?[算别不停]\w{0,3}了?吧?$", sentence) or re.match(
        r"^那?(?:[给帮]我)?取消了?吧?$", sentence
    ):
        return True

    return False


class CommandDebounce:
    debounced: DefaultDict[Type[Matcher], Set[str]] = defaultdict(set)

    class IsolateLevel(IntEnum):
        GLOBAL = auto()
        GROUP = auto()
        USER = auto()
        GROUP_USER = auto()

    def __init__(
        self,
        matcher: Type[Matcher],
        isolate_level: IsolateLevel = IsolateLevel.USER,
        debounce_timeout: float = 5,
        cancel_message: Optional[str] = None,
    ):
        self.isolate_level = isolate_level
        self.debounce_timeout = debounce_timeout
        self.matcher = matcher
        self.cancel_message = cancel_message

    async def __call__(self, bot: Bot, event: Event, state: T_State) -> bool:
        if not isinstance(event, MessageEvent):
            return True

        loop = get_running_loop()
        debounce_set = CommandDebounce.debounced[self.matcher]

        if self.isolate_level is self.IsolateLevel.GROUP:
            if isinstance(event, GroupMessageEvent):
                key = str(event.group_id)
            else:
                key = str(event.user_id)
        elif self.isolate_level is self.IsolateLevel.USER:
            key = str(event.user_id)
        elif self.isolate_level is self.IsolateLevel.GROUP_USER:
            key = (
                event.get_user_id()
                + "_"
                + str(event.group_id if isinstance(event, GroupMessageEvent) else "")
            )
        else:
            key = self.IsolateLevel.GLOBAL.name

        if key in debounce_set:
            if self.cancel_message is not None:
                await bot.send(event, self.cancel_message, at_sender=True)
            return False
        else:
            debounce_set.add(key)
            loop.call_later(self.debounce_timeout, lambda: debounce_set.remove(key))
            return True
