from io import BytesIO
from typing import Optional

from httpx import AsyncClient
from IzumiBot.plugins.message_template import Template
from nonebot.adapters.cqhttp import Bot, Message, MessageEvent, MessageSegment
from nonebot.adapters.cqhttp.utils import escape
from nonebot.plugin import on_command
from nonebot.typing import T_State

from .models import AnimeResult


def escape_message(msg) -> str:
    return escape(str(msg))


def image(url: str) -> str:
    return str(MessageSegment.image(url))


def raw(msg) -> str:
    return str(msg)


TEMPLATE = Template(
    """以下为以图搜番结果:
    {% each item in data.result max 3 %}--------
    {% if item.anilist.isAdult %}(NSFW Content){% else %}{{item.image|image}}{% end %}
    番剧名称:{{ item.anilist.title.native }}
    相似度:{{item.similarity}}{% end %}
""",
    filters=[escape_message, raw, image],
    default_filter="escape_message",
)


anime_search = on_command("anime_search", aliases={"搜番", "以图搜番"})


@anime_search.handle()
async def search_arg_parse(bot: Bot, event: MessageEvent, state: T_State):
    image: Optional[MessageSegment] = next(
        filter(lambda x: x.type == "image", event.message), None  # type:ignore
    )
    if image is not None:
        state["image"] = image.data["url"]
    else:
        await anime_search.reject("图呢?", at_sender=True)


@anime_search.got("image")
async def search_anime(bot: Bot, event: MessageEvent, state: T_State):
    await anime_search.send("在搜了")
    async with AsyncClient() as client:
        image_response = await client.get(state["image"])
        image_raw = image_response.content

        response = await client.post(
            "https://api.trace.moe/search",
            params={"anilistInfo": True},
            files={"image": BytesIO(image_raw)},
        )
        data = AnimeResult.parse_obj(response.json())

    result = data.result
    if not result:
        await anime_search.finish(data.error)

    result.sort(key=lambda item: item.similarity, reverse=True)
    message = Message(Message._construct(TEMPLATE.render(data=data)))

    await anime_search.finish(message, at_sender=True)
