import asyncio
import base64
import logging
from contextlib import asynccontextmanager
from typing import Awaitable, Callable

from hume.client import AsyncHumeClient
from hume.empathic_voice.types import AudioInput, AudioConfiguration, SessionSettings

logger = logging.getLogger(__name__)

try:
    from hume.empathic_voice.chat.socket_client import ChatConnectOptions
except ImportError:
    ChatConnectOptions = None  # type: ignore[misc, assignment]

MessageCallback = Callable[..., Awaitable[None]]
CloseCallback = Callable[[], Awaitable[None]]


class HumeEVIClient:
    """WebSocket client for Hume Empathic Voice Interface (EVI)."""

    def __init__(self, api_key: str, config_id: str, system_prompt: str = "") -> None:
        self.api_key = api_key
        self.config_id = config_id
        self.system_prompt = system_prompt
        self._client: AsyncHumeClient | None = None
        self._socket = None
        self._listener_task: asyncio.Task | None = None

    @asynccontextmanager
    async def connect(
        self,
        on_message_callback: MessageCallback,
        on_close_callback: CloseCallback,
    ):
        """Opens WebSocket with Hume EVI and yields when ready to stream audio."""
        self._client = AsyncHumeClient(api_key=self.api_key)

        connect_kwargs = {"config_id": self.config_id}
        if self.system_prompt:
            connect_kwargs["session_settings"] = {
                "system_prompt": self.system_prompt,
                "audio": {
                    "encoding": "linear16",
                    "sample_rate": 16000,
                    "channels": 1,
                },
            }

        use_callbacks = hasattr(self._client.empathic_voice.chat, "connect_with_callbacks")

        if use_callbacks and ChatConnectOptions is not None:
            options = ChatConnectOptions(config_id=self.config_id)
            if self.system_prompt:
                options["session_settings"] = connect_kwargs.get("session_settings")

            async with self._client.empathic_voice.chat.connect_with_callbacks(
                options=options,
                on_open=lambda: logger.info("Hume EVI connected"),
                on_message=on_message_callback,
                on_close=on_close_callback,
                on_error=lambda err: logger.error("Hume EVI error: %s", err),
            ) as socket:
                self._socket = socket
                await self._ensure_session_settings()
                try:
                    yield self
                finally:
                    await self.close()
        else:
            async with self._client.empathic_voice.chat.connect(**connect_kwargs) as socket:
                self._socket = socket
                await self._ensure_session_settings()

                async def listen() -> None:
                    try:
                        async for message in socket:
                            await on_message_callback(message)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        logger.error("Hume listener error: %s", exc)
                    finally:
                        await on_close_callback()

                self._listener_task = asyncio.create_task(listen())
                try:
                    yield self
                finally:
                    if self._listener_task and not self._listener_task.done():
                        self._listener_task.cancel()
                        try:
                            await self._listener_task
                        except asyncio.CancelledError:
                            pass
                    await self.close()

    async def _ensure_session_settings(self) -> None:
        """Send PCM session settings if not passed at connect time."""
        if not self._socket:
            return

        settings = SessionSettings(
            audio=AudioConfiguration(
                encoding="linear16",
                sample_rate=16000,
                channels=1,
            ),
        )
        if self.system_prompt:
            settings = SessionSettings(
                system_prompt=self.system_prompt,
                audio=AudioConfiguration(
                    encoding="linear16",
                    sample_rate=16000,
                    channels=1,
                ),
            )

        await self._socket.send_session_settings(settings)
        logger.info("Hume EVI session settings sent")

    async def send_audio(self, audio_bytes: bytes) -> None:
        """Sends a PCM audio chunk to Hume EVI."""
        if not self._socket:
            return

        encoded = base64.b64encode(audio_bytes).decode("utf-8")
        await self._socket.send_audio_input(AudioInput(data=encoded))

    async def close(self) -> None:
        """Gracefully closes the WebSocket connection."""
        self._socket = None
        self._client = None
