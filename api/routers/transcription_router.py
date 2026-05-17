"""WebSocket router for real-time audio transcription via Deepgram."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from deepgram import DeepgramClient
from deepgram.listen.v1.types import ListenV1Results

from ..config import settings
from ..database.redis_client import pubsub as redis_pubsub

logger = logging.getLogger(__name__)

router = APIRouter()

_active_sessions: dict[str, Any] = {}


@router.websocket("/ws/transcribe/{session_id}")
async def transcription_websocket(
    websocket: WebSocket,
    session_id: str,
    user_id: str = Query(...),
) -> None:
    """
    WebSocket endpoint for real-time audio transcription.

    Client sends raw PCM audio chunks (16kHz, mono, int16).
    Server sends back JSON: {type: "partial"|"final", text: str}
    """
    await websocket.accept()
    logger.info(f"Transcription WS opened: session={session_id} user={user_id}")

    dg_client = DeepgramClient(api_key=settings.DEEPGRAM_API_KEY)
    question_buffer: list[str] = []

    try:
        async with dg_client.listen.v1.connect(
            model="nova-3",
            language="en-IN",
            punctuate=True,
            smart_format=True,
            interim_results=True,
            endpointing=300,
            utterance_end_ms=1000,
            encoding="linear16",
            sample_rate=16000,
        ) as dg_connection:
            _active_sessions[session_id] = {"ws": websocket, "dg": dg_connection}

            async def receive_audio() -> None:
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        if data:
                            await dg_connection.send_media(data)
                except WebSocketDisconnect:
                    pass
                except Exception as e:
                    logger.debug(f"Audio receive error: {e}")

            async def process_transcripts() -> None:
                try:
                    async for event in dg_connection:
                        if not isinstance(event, ListenV1Results):
                            continue
                        try:
                            alts = event.channel.alternatives
                            if not alts:
                                continue
                            transcript = alts[0].transcript
                            is_final = event.is_final or False
                            speech_final = event.speech_final or False

                            if not transcript.strip():
                                continue

                            if is_final or speech_final:
                                question_buffer.append(transcript.strip())
                                full_text = " ".join(question_buffer[-5:])

                                await websocket.send_json({"type": "final", "text": transcript.strip()})
                                await redis_pubsub.publish(
                                    f"transcript:{session_id}",
                                    {"type": "final", "text": full_text, "session_id": session_id},
                                )

                                if speech_final:
                                    question_buffer.clear()
                            else:
                                await websocket.send_json({"type": "partial", "text": transcript.strip()})
                        except Exception as e:
                            logger.debug(f"Transcript handler error: {e}")
                except Exception as e:
                    logger.error(f"Deepgram stream error in session {session_id}: {e}")
                    try:
                        await websocket.send_json({"type": "error", "message": str(e)})
                    except Exception:
                        pass

            await asyncio.gather(receive_audio(), process_transcripts())

    except WebSocketDisconnect:
        logger.info(f"Transcription WS closed: session={session_id}")
    except Exception as e:
        logger.error(f"Transcription WS error: {e}")
    finally:
        _active_sessions.pop(session_id, None)


@router.websocket("/ws/answers/{session_id}")
async def answer_stream_websocket(
    websocket: WebSocket,
    session_id: str,
) -> None:
    """
    WebSocket that pushes streamed answer tokens to the Electron overlay.
    Subscribes to Redis pub/sub channel for this session.
    """
    await websocket.accept()
    logger.info(f"Answer stream WS opened: session={session_id}")

    try:
        async for message in redis_pubsub.subscribe(f"answer:{session_id}"):
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(str(message))
    except WebSocketDisconnect:
        logger.info(f"Answer stream WS closed: session={session_id}")
    except Exception as e:
        logger.error(f"Answer stream WS error: {e}")
