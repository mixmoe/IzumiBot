import nonebot
from fastapi import FastAPI
from nonebot.adapters.cqhttp import Bot as CQHTTPBot

nonebot.init()
app: FastAPI = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter("cqhttp", CQHTTPBot)  # type:ignore

nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()
