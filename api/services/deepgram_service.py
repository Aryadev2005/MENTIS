"""Deepgram Nova-3 real-time transcription service."""

import asyncio
import logging
from typing import Callable

from deepgram import DeepgramClient
from deepgram.listen.v1.types import ListenV1Results

from ..config import settings

logger = logging.getLogger(__name__)

TranscriptCallback = Callable[[str, bool], None]


class DeepgramTranscriber:
    """Manages a single Deepgram WebSocket connection for real-time transcription."""

    def __init__(
        self,
        on_partial: TranscriptCallback | None = None,
        on_final: TranscriptCallback | None = None,
    ):
        self.on_partial = on_partial
        self.on_final = on_final
        self._audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
        self._is_active = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._is_active = True
        self._task = asyncio.create_task(self._run())
        logger.info("Deepgram transcription started")

    async def send_audio(self, chunk: bytes) -> None:
        if self._is_active:
            await self._audio_queue.put(chunk)

    async def stop(self) -> None:
        self._is_active = False
        await self._audio_queue.put(None)
        if self._task:
            await self._task
        logger.info("Deepgram transcription stopped")

    async def _run(self) -> None:
        client = DeepgramClient(api_key=settings.DEEPGRAM_API_KEY)
        try:
            async with client.listen.v1.connect(
                model="nova-3",
                language="en-IN",
                punctuate=True,
                smart_format=True,
                interim_results=True,
                endpointing=300,
                utterance_end_ms=1000,
                encoding="linear16",
                sample_rate=16000,
            ) as connection:
                async def feed_audio() -> None:
                    while self._is_active:
                        chunk = await self._audio_queue.get()
                        if chunk is None:
                            break
                        await connection.send_media(chunk)

                async def read_transcripts() -> None:
                    async for event in connection:
                        if not isinstance(event, ListenV1Results):
                            continue
                        try:
                            alts = event.channel.alternatives
                            if not alts:
                                continue
                            transcript = alts[0].transcript
                            is_final = event.is_final or False
                            speech_final = event.speech_final or False

                            if not transcript or not transcript.strip():
                                continue

                            if speech_final or is_final:
                                if self.on_final:
                                    self.on_final(transcript.strip(), True)
                                logger.debug(f"Final transcript: {transcript[:100]}")
                            else:
                                if self.on_partial:
                                    self.on_partial(transcript.strip(), False)
                        except (AttributeError, IndexError) as e:
                            logger.debug(f"Transcript parse error: {e}")

                await asyncio.gather(feed_audio(), read_transcripts())
        except Exception as e:
            logger.error(f"Deepgram session error: {e}")
        finally:
            self._is_active = False

    @property
    def is_active(self) -> bool:
        return self._is_active


async def transcribe_file(audio_path: str) -> str:
    """Transcribe a complete audio file."""
    client = DeepgramClient(api_key=settings.DEEPGRAM_API_KEY)

    with open(audio_path, "rb") as audio_file:
        buffer_data = audio_file.read()

    response = await client.listen.v1.media.transcribe_file(
        request=buffer_data,
        model="nova-3",
        language="en-IN",
        punctuate=True,
        smart_format=True,
    )

    channels = response.results.channels
    if not channels or not channels[0].alternatives:
        return ""
    return channels[0].alternatives[0].transcript or ""
