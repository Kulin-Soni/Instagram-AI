import asyncio
import logging
from aiograpi import Client
from config import CUSTOM_DEVICE_CONFIG, PASSWORD, SESSION_FILE, USERNAME

async def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s - %(levelname)s] %(name)s: %(message)s",
    )
    cl = Client()
    if SESSION_FILE.exists():
        cl.load_settings(SESSION_FILE)
        cl.set_device(CUSTOM_DEVICE_CONFIG)
    await cl.login(username=USERNAME, password=PASSWORD, verification_code=input("2FA Code:"))
    cl.dump_settings(SESSION_FILE)

asyncio.run(main())
