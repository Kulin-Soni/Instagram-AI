from ollama import AsyncClient

from config import OLLAMA_HOST, OLLAMA_MODEL
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
