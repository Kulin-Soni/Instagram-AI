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
                        break
                except httpx.HTTPStatusError:
                    logger.info("Waiting for ollama to be ready...")
                    await asyncio.sleep(1)

            timeout = 120
            while True:
                try:
                    (await session.post(
                        f'{OLLAMA_HOST}/api/generate',
                        json={
                            "model": OLLAMA_MODEL,
                            "prompt": "hi",
                            "options": {"num_predict": 1},
                            "stream": False
                        },
                        timeout=timeout
                    )).raise_for_status()
                    break
                except Exception:
                    logger.info("Waiting for model to load...")
                    timeout += 10
                await asyncio.sleep(2)
            logger.info("Model loaded successfully!")
