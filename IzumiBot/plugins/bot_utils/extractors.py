import re
from typing import List, Optional

from nonebot.adapters.cqhttp import Message, MessageSegment

NUMBER_MATCH_REGEXP = re.compile(r"[+-]?(\d*\.?\d+|\d+\.?\d*)")


def extract_image(message: Message) -> Optional[str]:
    for segment in message:
        segment: MessageSegment  # type:ignore
        if segment.type == "image":
            return segment.data["url"]
    return None


def extract_text(message: Message) -> str:
    text = ""
    for segment in message:
        segment: MessageSegment  # type:ignore
        if segment.is_text():
            text += str(segment)
    return text


def extract_numbers(message: Message) -> List[float]:
    text = extract_text(message)
    return [*map(float, NUMBER_MATCH_REGEXP.findall(text))]
