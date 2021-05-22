from typing import List, Optional

from nonebot.adapters.cqhttp import Message

from .extractors import extract_text

NATURAL_POSITIVE_WORD = {
    "要",
    "用",
    "是",
    "好",
    "对",
    "嗯",
    "行",
    "ok",
    "okay",
    "yeah",
    "yep",
    "当真",
    "当然",
    "必须",
    "可以",
    "肯定",
    "没错",
    "确定",
    "确认",
}

NATURAL_NEGATIVE_WORD = {
    "不",
    "不要",
    "不用",
    "不是",
    "否",
    "不好",
    "不对",
    "不行",
    "别",
    "no",
    "nono",
    "nonono",
    "nope",
    "不ok",
    "不可以",
    "不能",
    "不可以",
}


def convert_chinese_to_boolean(message: Message) -> Optional[bool]:
    text = (
        extract_text(message)
        .strip()
        .lower()
        .replace(" ", "")
        .rstrip(",.!?~，。！？～了的呢吧呀啊呗啦")
    )
    if text in NATURAL_POSITIVE_WORD:
        return True
    if text in NATURAL_NEGATIVE_WORD:
        return False
    return None


def strip_nonempty_lines(message: Message) -> List[str]:
    return [line for line in extract_text(message).splitlines() if line]


def strip_nonempty_stripped_lines(message: Message) -> List[str]:
    return [line.strip() for line in extract_text(message).splitlines() if line.strip()]
