from collections import OrderedDict
from beanie import Document
from pydantic import BaseModel
from config import MAX_MSGS

class Msg(BaseModel):
    author: str
    content: str
    msg_id: str
    replying_to: str | None = None


class InstagramChat(Document):
    chats: OrderedDict[str, Msg]
    thread_id: str
    users: dict[str, str]

    class Settings:
        name = "chats"

    @classmethod
    async def get_or_create(cls, thread_id: str) -> "InstagramChat":
        if chat := await InstagramChat.find_one(InstagramChat.thread_id == thread_id):
            return chat

        chat = cls(chats=OrderedDict(), thread_id=thread_id, users={})
        return await chat.insert()

    async def add_to_chat(
        self, chat: Msg | OrderedDict[str, Msg] | list[Msg]
    ) -> OrderedDict[str, Msg]:
        if isinstance(chat, list):
            for msg in chat:
                self.chats[msg.msg_id] = msg
        elif isinstance(chat, OrderedDict):
            self.chats.update(chat)
        else:
            self.chats[chat.msg_id] = chat

        total = len(self.chats)
        if total > MAX_MSGS:
            self.chats = OrderedDict(list(self.chats.items())[-MAX_MSGS:])

        await self.save()
        return self.chats
