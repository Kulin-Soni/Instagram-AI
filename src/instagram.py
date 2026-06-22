"""
Instagram AI bot client — handles login, real-time DM listening,
and AI-powered reply generation.
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime
import socket
from typing import Any, OrderedDict

from aiograpi import Client
from aiograpi.mixins.challenge import ChallengeChoice
from aiograpi.types import DirectMessage, DirectThread

from ai import AISession
from config import CUSTOM_DEVICE_CONFIG, DEV_ID, MAX_MSGS, NAME, PASSWORD, SESSION_FILE, USERNAME
from models import InstagramChat, Msg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The real-time event type we care about; all others are silently ignored.
_REALTIME_NEW_MESSAGE_EVENT = "deltaNewMessage"

# Instagram timestamps are in microseconds; divide to get seconds for datetime.
_INSTAGRAM_TIMESTAMP_DIVISOR = 1_000_000

# Prefixes that trigger an AI reply — either an @mention or a slash-command.
_TRIGGER_PREFIXES: list[str] = [f"@{USERNAME}", f"/{NAME}"]

# ---------------------------------------------------------------------------
# Async input helper
# ---------------------------------------------------------------------------


async def _async_input(prompt: str = "") -> str:
    """Run blocking ``input()`` in an executor so it doesn't block the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)


# ---------------------------------------------------------------------------
# Display-name resolution
# ---------------------------------------------------------------------------


def _resolve_display_name(user_id: str, users: dict[str, str]) -> str:
    """
    Return the display name for *user_id* from *users*, falling back to
    ``"Anonymous"`` when the ID is absent or maps to an empty string.
    """
    return users.get(user_id) or "Anonymous"


# ---------------------------------------------------------------------------
# Trigger-prefix detection
# ---------------------------------------------------------------------------


def _find_matching_prefix(text: str, prefixes: list[str]) -> str | None:
    """
    Return the first entry in *prefixes* that *text* starts with, or
    ``None`` if no prefix matches.

    Unlike ``str.startswith``, this returns the matched prefix itself so
    the caller can strip it from the message body.
    """
    for prefix in prefixes:
        if text.startswith(prefix):
            return prefix
    return None


# ---------------------------------------------------------------------------
# Challenge handlers (standalone so they're easy to swap / test)
# ---------------------------------------------------------------------------


async def _challenge_code_handler(_: str, choice: ChallengeChoice) -> str | bool:
    """Prompt the user for a verification code delivered via SMS or email."""
    if choice == ChallengeChoice.SMS:
        return await _async_input("Enter the code sent to your SMS: ")
    if choice == ChallengeChoice.EMAIL:
        return await _async_input("Enter the code sent to your email: ")
    return False


async def _change_password_handler(_: str) -> str:
    """
    Generate and log a random replacement password when Instagram forces a
    password change during challenge resolution.

    The new password is logged at WARNING level so the operator can retrieve
    it — losing it would lock the account out.
    """
    chars = list("abcdefghijklmnopqrstuvwxyz1234567890!&£@#")
    new_password = "".join(random.sample(chars, 8))
    logger.warning(
        "Password changed during challenge resolution. New password: %s", new_password
    )
    return new_password


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------


class InstagramClient:
    """
    Async context-manager that logs into Instagram, subscribes to real-time
    DMs, and replies via an AI session when triggered by a recognized prefix.

    Usage::

        async with InstagramClient() as client:
            await client.listen_for_messages()
    """

    # Seconds to wait before reconnecting after a transient failure.
    _RECONNECT_DELAY_ON_TIMEOUT: int = 1
    _RECONNECT_DELAY_ON_ERROR: int = 1

    def __init__(self, *, logout_on_exit: bool = False) -> None:
        self._client = Client()
        self._ai = AISession()

        self._username: str | None = None
        self._logout_on_exit = logout_on_exit

        # Cache of active chats keyed by thread_id to avoid redundant API calls.
        self._chats: dict[str, InstagramChat] = {}

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> InstagramClient:
        await self._login()
        logger.info("Logged in as @%s", self._username)
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._logout_on_exit:
            await self._client.logout()

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    async def _login(self) -> None:
        """
        Configure the underlying client and authenticate with Instagram.

        Loads an existing session file when available to avoid unnecessary
        login round-trips; always persists a fresh session file on success.

        Raises:
            RuntimeError: If the Instagram login call returns falsy.
        """
        self._username = USERNAME
        self._client.delay_range = [1, 5]
        self._client.challenge_code_handler = _challenge_code_handler
        self._client.change_password_handler = _change_password_handler
        self._client.set_device(CUSTOM_DEVICE_CONFIG)

        if SESSION_FILE.exists():
            self._client.load_settings(SESSION_FILE)

        if not await self._client.login(USERNAME, PASSWORD):
            raise RuntimeError("Instagram login failed.")

        self._client.dump_settings(SESSION_FILE)

    # ------------------------------------------------------------------
    # Thread / chat helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_thread_users(thread: DirectThread) -> dict[str, str]:
        """Return a ``pk → full_name`` mapping for every participant in *thread*."""
        return {user.pk: user.full_name for user in thread.users if user.full_name}

    async def _load_thread(self, thread_id: str, message_limit: int) -> InstagramChat:
        """
        Fetch recent messages for *thread_id* from the API, hydrate the local
        cache entry, and return the updated :class:`InstagramChat`.

        Only text messages that haven't been seen before are appended to the chat
        log, preventing duplicate processing on reconnects.

        NOTE: ``new_messages[:-1]`` intentionally excludes the *last* element of
        the fetched batch before persisting. The final message in the API response
        is typically the one that triggered this load and will be recorded
        separately by the caller — removing it here prevents a duplicate entry.
        Changing this would alter existing behavior.
        """
        fetched_thread = await self._client.direct_thread(int(thread_id), message_limit)
        chat = await InstagramChat.get_or_create(fetched_thread.id)
        users = self._extract_thread_users(fetched_thread)

        unseen_messages = [
            Msg(
                author=msg.user_id,  # type: ignore[arg-type]
                content=msg.text,
                msg_id=msg.id,
                replying_to=str(msg.reply.user_id) if msg.reply else None,
            )
            for msg in fetched_thread.messages
            if msg.item_type == "text" and msg.text and msg.id not in chat.chats
        ]

        chat.users = users
        # Exclude the last message — see NOTE in docstring.
        await chat.add_to_chat(unseen_messages[:-1])
        return chat

    def _build_ai_history(
        self, chat_log: OrderedDict[str, Msg], users: dict[str, str]
    ) -> list[dict[str, str]]:
        """
        Convert the ordered chat log into the role-based message format expected
        by the AI session (``{"role": "user"|"assistant", "content": "…"}``).

        Messages sent by this bot are mapped to the ``"assistant"`` role; all
        others become ``"user"`` messages, labelled with the sender's display name.
        """
        my_id = str(self._client.user_id)
        history: list[dict[str, str]] = []

        for msg in chat_log.values():
            sender_name = (
                "You"
                if msg.author == my_id
                else _resolve_display_name(str(msg.author), users)
            )

            reply_context = (
                f" replying to {_resolve_display_name(str(msg.replying_to), users)}"
                if msg.replying_to
                else ""
            )

            role = "assistant" if msg.author == my_id else "user"
            content = f"{sender_name}{reply_context}: {msg.content}"

            history.append({"role": role, "content": content})

        return history

    # ------------------------------------------------------------------
    # Incoming message handling
    # ------------------------------------------------------------------

    async def _handle_message(self, payload: dict) -> None:
        """
        Process a single incoming real-time payload end-to-end:

        1. Ignore non-DM events.
        2. Validate all required fields are present and well-typed.
        3. Resolve (or lazily load) the thread from the local cache.
        4. Persist the new message.
        5. If the message targets this bot, generate and send an AI reply.
        """
        if payload.get("delta_type") != _REALTIME_NEW_MESSAGE_EVENT:
            return

        raw_message = payload.get("message")
        if not isinstance(raw_message, dict):
            return

        # Validate and extract all required fields in one pass.
        fields = self._parse_message_fields(raw_message)
        if fields is None:
            return

        thread_id, msg_id, context, timestamp, text, user_id, replied_to_raw = fields

        # Resolve the thread from cache, fetching from the API on first sight.
        if thread_id not in self._chats:
            self._chats[thread_id] = await self._load_thread(thread_id, MAX_MSGS * 2)
        chat = self._chats[thread_id]

        # Guard against duplicate delivery of the same message.
        if msg_id in chat.chats:
            return

        replying_to_id = self._extract_reply_author_id(replied_to_raw)
        author_display_name = _resolve_display_name(str(user_id), chat.users)

        await chat.add_to_chat(
            Msg(
                author=str(user_id),
                content=text,
                msg_id=msg_id,
                replying_to=replying_to_id,
            )
        )

        # Only respond when the message explicitly mentions or commands this bot.
        matched_prefix = _find_matching_prefix(text, _TRIGGER_PREFIXES)
        if not matched_prefix:
            return

        await self._generate_and_send_reply(
            chat=chat,
            thread_id=thread_id,
            msg_id=msg_id,
            context=context,
            timestamp=timestamp,
            user_id=str(user_id),
            author_display_name=author_display_name,
            message_body=text.removeprefix(matched_prefix),
        )

    @staticmethod
    def _parse_message_fields(
        raw: dict,
    ):
        """
        Extract and type-check all required fields from a raw message dict.

        Returns a structured tuple on success, or ``None`` if any field is
        missing or has an unexpected type — allowing the caller to bail early
        without a cascade of nested ``isinstance`` checks.
        """
        thread_id = raw.get("thread_id")
        msg_id = raw.get("item_id")
        context = raw.get("client_context")
        timestamp = raw.get("timestamp")
        text = raw.get("text")
        user_id = raw.get("user_id")
        replied_to_raw = raw.get("replied_to_message")  # optional — not validated here

        if not all(
            [
                isinstance(thread_id, (int, str)),
                isinstance(msg_id, (int, str)),
                isinstance(context, str),
                isinstance(user_id, (int, str)),
                isinstance(text, str),
                isinstance(timestamp, int),
            ]
        ):
            return None

        return (
            str(thread_id),
            str(msg_id),
            str(context),
            int(timestamp), # type: ignore
            str(text),
            str(user_id),
            replied_to_raw if isinstance(replied_to_raw, dict) else None,
        )

    @staticmethod
    def _extract_reply_author_id(replied_to_raw: dict | None) -> str | None:
        """
        Pull the author's user ID out of an optional reply-context dict.

        Returns ``None`` if the message is not a reply or the ID is absent.
        """
        if replied_to_raw is None:
            return None
        reply_author_id = replied_to_raw.get("user_id")
        if isinstance(reply_author_id, (int, str)):
            return str(reply_author_id)
        return None

    async def _generate_and_send_reply(
        self,
        *,
        chat: InstagramChat,
        thread_id: str,
        msg_id: str,
        context: str,
        timestamp: int,
        user_id: str,
        author_display_name: str,
        message_body: str,
    ) -> None:
        """
        Ask the AI session for a reply and deliver it to the thread.

        The sent message is immediately persisted to the local chat log so
        that the next AI history build reflects our reply.
        """
        prompt = f"{author_display_name} to You: {message_body}"
        history = self._build_ai_history(chat.chats, chat.users)
        response = await self._ai.chat(history=history, msg=prompt)

        if response is None:
            return

        # Convert Instagram's microsecond timestamp to a Python datetime.
        message_timestamp = datetime.fromtimestamp(
            timestamp / _INSTAGRAM_TIMESTAMP_DIVISOR
        )

        sent_message = await self._client.direct_send(
            response,
            thread_ids=[int(thread_id)],
            reply_to_message=DirectMessage(
                id=msg_id,
                client_context=context,
                timestamp=message_timestamp,  # type: ignore[arg-type]
            ),
        )

        my_id = str(self._client.user_id)
        await chat.add_to_chat(
            Msg(
                author=my_id,
                content=response,
                msg_id=sent_message.id,
                replying_to=user_id,
            )
        )

    # ------------------------------------------------------------------
    # Real-time sync callback
    # ------------------------------------------------------------------

    def _on_realtime_message(self, payload: dict) -> None:
        """
        Synchronous callback registered with the real-time client.

        Schedules the async handler on the running event loop without blocking
        the real-time read loop.
        """
        asyncio.get_event_loop().create_task(self._handle_message(payload))

    # ------------------------------------------------------------------
    # Real-time loop
    # ------------------------------------------------------------------

    async def listen_for_messages(self) -> None:
        """
        Subscribe to Instagram's real-time DM stream and reconnect
        automatically on timeouts or transient errors.

        This method runs indefinitely; cancel the enclosing task to stop it.
        """
        while True:
            try:
                await self._run_realtime_session()
            except TimeoutError:
                logger.warning(
                    "Real-time connection timed out — reconnecting in %ds…",
                    self._RECONNECT_DELAY_ON_TIMEOUT,
                    exc_info=True,
                )
                await asyncio.sleep(self._RECONNECT_DELAY_ON_TIMEOUT)
            except Exception:
                logger.warning(
                    "Real-time error — reconnecting in %ds…",
                    self._RECONNECT_DELAY_ON_ERROR,
                    exc_info=True,
                )
                await asyncio.sleep(self._RECONNECT_DELAY_ON_ERROR)

    async def _run_realtime_session(self) -> None:
        """
        Establish one real-time session and process messages until the
        connection drops or times out.

        The socket timeout is set to 60 s so a stalled connection is detected
        promptly and the outer reconnect loop can restart it.
        """
        self._client.realtime_on("message", self._on_realtime_message)
        realtime_session = await self._client.realtime_connect()
        realtime_session.transport.sock.settimeout(240)  # type: ignore[union-attr]
        realtime_session.transport.sock.setsockopt( # type: ignore
            socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1
        )
        await realtime_session.direct_subscribe()
        logger.info("Subscribed to live messages.")

        try:
            await realtime_session.ping()
            # Notify the developer account that the bot is online.
            if DEV_ID:
                await realtime_session.direct_send_text(DEV_ID, "Started!")

            while True:
                await realtime_session.read_once()
        finally:
            await self._client.realtime_disconnect()
