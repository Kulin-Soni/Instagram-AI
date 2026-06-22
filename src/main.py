import asyncio
import logging

from beanie import init_beanie
from pymongo import AsyncMongoClient
from ai import AISession
from config import MONGO_URI
from instagram import InstagramClient
from models import InstagramChat

logger = logging.getLogger(__name__)

async def init_mongo():
    client = AsyncMongoClient(MONGO_URI)
    await client.aconnect()
    await init_beanie(database=client["insta_ai"], document_models=[InstagramChat])
    logger.info("Connected to MongoDB")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s - %(levelname)s] %(name)s: %(message)s",
    )
    await init_mongo()
    await AISession.wait_for_ready()
    async with InstagramClient() as client:
        await client.listen_for_messages()


if __name__ == "__main__":
    asyncio.run(main())
