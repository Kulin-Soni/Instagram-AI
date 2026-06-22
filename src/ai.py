import asyncio

import httpx
import logging
from ollama import AsyncClient
from config import OLLAMA_HOST, OLLAMA_MODEL

logger = logging.getLogger(__name__)

class AISession:
    def __init__(self) -> None:
        self.client = AsyncClient(
            host=OLLAMA_HOST
        )
    async def chat(self, history: list[dict[str, str]], msg: str):
        res = await self.client.chat(
            model=OLLAMA_MODEL,
            messages=[
                *history, 
                {"role": "user", "content": msg}
            ]
        )
        try:
            return res.message.content
        except Exception:
            return

    @staticmethod
    async def wait_for_ready():
        async with httpx.AsyncClient() as session:
            while True:
                try:
                    res = await session.get(f'{OLLAMA_HOST}/api/tags')
                    res.raise_for_status()
                    tags = res.json()
                    if tags:
                        logger.info("Ollama is ready!")
                        return
                except httpx.HTTPStatusError:
                    logger.info("Waiting for ollama to be ready...")
                    await asyncio.sleep(1)
