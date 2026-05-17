"""Group OA WebSocket service — encrypted real-time solution sharing."""

import asyncio
import base64
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

try:
    from nacl.secret import SecretBox
    from nacl.utils import random as nacl_random
    _NACL_AVAILABLE = True
except ImportError:
    _NACL_AVAILABLE = False
    logger.warning("PyNaCl not installed — group OA encryption disabled")


MAX_MEMBERS = 6
SESSION_TTL_SECONDS = 3 * 60 * 60  # 3 hours


@dataclass
class GroupMember:
    websocket: WebSocket
    user_id: str
    joined_at: float = field(default_factory=time.time)


@dataclass
class GroupSession:
    group_code: str
    members: dict[str, GroupMember] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    solution_count: int = 0
    _box: Any = field(default=None, repr=False)

    def __post_init__(self):
        if _NACL_AVAILABLE:
            key = nacl_random(SecretBox.KEY_SIZE)
            self._box = SecretBox(key)
            self._key_b64 = base64.b64encode(key).decode()
        else:
            self._key_b64 = ""

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > SESSION_TTL_SECONDS

    @property
    def member_count(self) -> int:
        return len(self.members)

    def encrypt(self, data: dict) -> str:
        payload = json.dumps(data).encode()
        if self._box:
            encrypted = self._box.encrypt(payload)
            return base64.b64encode(encrypted).decode()
        return base64.b64encode(payload).decode()

    def decrypt(self, token: str) -> dict:
        data = base64.b64decode(token)
        if self._box:
            data = self._box.decrypt(data)
        return json.loads(data)


class GroupOAService:
    def __init__(self):
        self._sessions: dict[str, GroupSession] = {}
        self._cleanup_task: asyncio.Task | None = None

    def _get_or_create(self, group_code: str) -> GroupSession:
        if group_code in self._sessions:
            session = self._sessions[group_code]
            if session.is_expired:
                del self._sessions[group_code]
            else:
                return session

        session = GroupSession(group_code=group_code)
        self._sessions[group_code] = session
        return session

    async def connect(self, group_code: str, user_id: str, websocket: WebSocket) -> bool:
        """Add a member to a group session. Returns False if group is full."""
        session = self._get_or_create(group_code)

        if session.member_count >= MAX_MEMBERS and user_id not in session.members:
            await websocket.send_json({
                "type": "error",
                "message": f"Group is full (max {MAX_MEMBERS} members)",
            })
            return False

        session.members[user_id] = GroupMember(websocket=websocket, user_id=user_id)

        await websocket.send_json({
            "type": "joined",
            "group_code": group_code,
            "member_count": session.member_count,
            "encryption": _NACL_AVAILABLE,
            "expires_in": int(SESSION_TTL_SECONDS - (time.time() - session.created_at)),
        })

        await self._broadcast(session, {
            "type": "member_joined",
            "user_id": user_id,
            "member_count": session.member_count,
        }, exclude=user_id)

        logger.info("User %s joined group %s (%d members)", user_id, group_code, session.member_count)
        return True

    async def disconnect(self, group_code: str, user_id: str):
        session = self._sessions.get(group_code)
        if not session or user_id not in session.members:
            return

        del session.members[user_id]

        if session.member_count == 0:
            del self._sessions[group_code]
            logger.info("Group %s dissolved (no members)", group_code)
            return

        await self._broadcast(session, {
            "type": "member_left",
            "user_id": user_id,
            "member_count": session.member_count,
        })

    async def broadcast_solution(self, group_code: str, sender_id: str, solution: dict):
        """Send OA solution to all group members except the sender."""
        session = self._sessions.get(group_code)
        if not session:
            return

        session.solution_count += 1

        payload = {
            "type": "solution",
            "from_user": sender_id,
            "solution": solution,
            "solution_number": session.solution_count,
        }

        if _NACL_AVAILABLE and session._box:
            encrypted_token = session.encrypt(payload)
            message = {
                "type": "encrypted_solution",
                "token": encrypted_token,
            }
        else:
            message = payload

        await self._broadcast(session, message, exclude=sender_id)
        logger.info("Solution #%d broadcast to %d members in group %s",
                    session.solution_count, session.member_count - 1, group_code)

    async def _broadcast(self, session: GroupSession, message: dict, exclude: str | None = None):
        dead_members = []
        for user_id, member in session.members.items():
            if user_id == exclude:
                continue
            try:
                await member.websocket.send_json(message)
            except Exception:
                dead_members.append(user_id)

        for uid in dead_members:
            del session.members[uid]

    async def handle_connection(self, group_code: str, user_id: str, websocket: WebSocket):
        """Main WebSocket handler loop for a group member."""
        await websocket.accept()

        joined = await self.connect(group_code, user_id, websocket)
        if not joined:
            await websocket.close(code=4003)
            return

        try:
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")

                if msg_type == "solution":
                    solution = data.get("solution", {})
                    await self.broadcast_solution(group_code, user_id, solution)

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "status":
                    session = self._sessions.get(group_code)
                    if session:
                        await websocket.send_json({
                            "type": "status",
                            "member_count": session.member_count,
                            "solution_count": session.solution_count,
                            "expires_in": int(SESSION_TTL_SECONDS - (time.time() - session.created_at)),
                        })

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.error("Group WS error for %s in %s: %s", user_id, group_code, e)
        finally:
            await self.disconnect(group_code, user_id)

    def get_active_groups(self) -> list[dict]:
        return [
            {
                "group_code": code,
                "member_count": s.member_count,
                "solution_count": s.solution_count,
                "age_seconds": int(time.time() - s.created_at),
            }
            for code, s in self._sessions.items()
            if not s.is_expired
        ]

    async def cleanup_expired(self):
        expired = [code for code, s in self._sessions.items() if s.is_expired]
        for code in expired:
            session = self._sessions.pop(code)
            for member in session.members.values():
                try:
                    await member.websocket.close(code=4000)
                except Exception:
                    pass
            logger.info("Expired group session %s cleaned up", code)
        return len(expired)


group_oa_service = GroupOAService()
