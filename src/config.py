import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(".env")

MAX_MSGS = 10

CUSTOM_DEVICE_CONFIG = {
            "android_version": 33,
            "android_release": "13",
            "dpi": "420dpi",
            "resolution": "1080x2400",
            "manufacturer": "Samsung/samsung",
            "device": "a54",
            "model": "Galaxy A54",
            "cpu": "a54",
        }

SESSION_FILE = Path("session.json")

USERNAME = os.getenv("INSTA_USERNAME")
NAME = os.getenv("NAME")
PASSWORD = os.getenv("INSTA_PASSWORD")
DEV_ID = os.getenv("DEV_ID")

MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_PORT = os.getenv("MONGO_PORT")
MONGO_URI = f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@mongo:{MONGO_PORT}/"

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")
OLLAMA_PORT = os.getenv("OLLAMA_PORT")
OLLAMA_HOST = f"http://ollama:{OLLAMA_PORT}"
