import asyncio
import json
import logging
from typing import Any

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone
from graphene.validation import depth_limit_validator
from graphql import DocumentNode, parse, validate

from api.schema import schema as graphql_schema
from main.chat.subscriptions import ChatSubscriptionHandler
from shared.errors.mu_error import MUError


def _safe_error_payload(exc: Exception) -> dict[str, Any]:
    """Only echo curated MUError messages; everything else gets a generic
    label so internal exception strings don't leak over the wire."""
    if isinstance(exc, MUError):
        payload: dict[str, Any] = {"message": exc.message}
        if getattr(exc, "code", None) is not None:
            payload["extensions"] = { "code": int(exc.code) }
        return payload
    logger.exception("Unhandled WS error")
    return {"message": "Internal error"}

logger = logging.getLogger(__name__)


@database_sync_to_async
def get_session(token: str) -> Session:
    return Session.objects.get(
        session_key=token, expire_date__gt=timezone.now()
    )


class GraphQLSubscriptionConsumer(AsyncWebsocketConsumer):

    async def connect(self) -> None:
        await self.accept(subprotocol="graphql-transport-ws")
        self.subscriptions: dict[str, Any] = {}
        self.keep_alive_task: asyncio.Task | None = None
        self._chat_handler = ChatSubscriptionHandler(self)
        self.scope["user_id"] = None
        self._init_timeout_task = asyncio.create_task(self._enforce_init_timeout())

    async def _enforce_init_timeout(self) -> None:
        try:
            await asyncio.sleep(settings.WS_CONNECTION_INIT_TIMEOUT_SECONDS)
        except asyncio.CancelledError:
            return
        if self.scope.get("user_id") is None:
            logger.debug("WebSocket connection_init timed out")
            await self.close(code=4408)

    async def disconnect(self, close_code: int) -> None:
        if self.keep_alive_task:
            self.keep_alive_task.cancel()
        if getattr(self, "_init_timeout_task", None):
            self._init_timeout_task.cancel()
        for sub_id in list(self.subscriptions.keys()):
            await self.cleanup_subscription(sub_id)
        await self._chat_handler.disconnect()

    async def receive(self, text_data: str = "", bytes_data: bytes = None) -> None:
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "connection_init":
                await self.handle_connection_init(data)
            elif message_type in ("subscribe",):
                await self.handle_start(data)
            elif message_type == "stop":
                await self.handle_stop(data)
            elif message_type == "complete":
                await self.handle_stop(data)
            elif message_type == "pong":
                pass
            else:
                await self.send_message(
                    "error", None, {"message": "Unknown message type"}
                )

        except json.JSONDecodeError:
            await self.send_message("error", None, {"message": "Invalid JSON"})

    async def handle_connection_init(self, data: dict[str, Any]) -> None:
        payload = data.get("payload") or {}
        token = (
            payload.get("Authorization")
            or payload.get("authorization")
            or payload.get("token")
        )

        if token:
            try:
                session = await get_session(token)
                session = session.get_decoded()
                user_id = session.get("_auth_user_id")
                if user_id:
                    self.scope["user_id"] = user_id
                    logger.debug("WebSocket authenticated user %s", user_id)
                else:
                    logger.debug("WebSocket session has no user_id")
                    await self.send_message(
                        "error", None, {"message": "Authentication failed"}
                    )
                    await self.close()
                    return
            except Session.DoesNotExist:
                logger.debug("WebSocket session not found for token")
                await self.send_message("error", None, {"message": "Invalid session"})
                await self.close()
                return
        else:
            # Try scope user from AuthMiddlewareStack (cookie-based)
            user = self.scope.get("user")
            if user and hasattr(user, "id") and user.id is not None:
                self.scope["user_id"] = user.id
                logger.debug("WebSocket authenticated user %s via cookie", user.id)
            else:
                logger.debug("WebSocket connection has no auth token or cookie")
                await self.send_message(
                    "error", None, {"message": "Authentication required"}
                )
                await self.close()
                return

        if getattr(self, "_init_timeout_task", None):
            self._init_timeout_task.cancel()
            self._init_timeout_task = None
        await self.send_message("connection_ack")
        self.keep_alive_task = asyncio.create_task(self.send_keep_alive())

    async def send_keep_alive(self) -> None:
        while True:
            await asyncio.sleep(settings.WS_KEEPALIVE_INTERVAL_SECONDS)
            try:
                await self.send_message("ping")
            except Exception:
                break

    async def handle_start(self, data: dict[str, Any]) -> None:
        subscription_id = data.get("id")

        if self.scope.get("user_id") is None:
            await self.close(code=4401)
            return

        payload = data.get("payload")
        query = payload.get("query")
        variables = payload.get("variables", {})
        operation_name = payload.get("operationName")

        if not query or not subscription_id:
            await self.send_message(
                "error",
                subscription_id,
                {"message": "Missing query or subscription ID"},
            )
            return

        try:
            document = parse(query)
            validation_errors = validate(
                graphql_schema.graphql_schema,
                document,
                rules=[depth_limit_validator(max_depth=settings.GRAPHQL_MAX_QUERY_DEPTH)],
            )

            if validation_errors:
                await self.send_message(
                    "error",
                    subscription_id,
                    {"errors": [e.message for e in validation_errors]},
                )
                return

            # Extract subscription field name from AST
            field_name = self._get_subscription_field(document)

            if field_name == "myChats":
                await self._chat_handler.start_my_chats(subscription_id)
                return

            if field_name in ("chatMessages", "chatLastOpen"):
                chat_id = variables.get("chatId")
                if chat_id is None:
                    await self.send_message(
                        "error", subscription_id, {"message": "chatId is required"}
                    )
                    return
                if field_name == "chatMessages":
                    await self._chat_handler.start_chat_messages(
                        subscription_id, chat_id
                    )
                else:
                    await self._chat_handler.start_chat_last_open(
                        subscription_id, chat_id
                    )
                return

            # Fallback: existing schema.subscribe path
            result = await graphql_schema.subscribe(
                query=query,
                variable_values=variables,
                operation_name=operation_name,
                context_value=self.get_context(),
            )

            if hasattr(result, "__aiter__"):
                self.subscriptions[subscription_id] = result
                asyncio.create_task(
                    self.handle_subscription_results(subscription_id, result)
                )
            else:
                await self.send_message("next", subscription_id, {"data": result.data})
                await self.send_message("complete", subscription_id)

        except Exception as e:
            await self.send_message(
                "error", subscription_id, _safe_error_payload(e)
            )

    def _get_subscription_field(self, document: DocumentNode) -> str | None:
        for definition in document.definitions:
            if definition.operation and definition.operation.value == "subscription":
                if definition.selection_set and definition.selection_set.selections:
                    return definition.selection_set.selections[0].name.value
        return None

    async def chat_message(self, event: dict[str, Any]) -> None:
        """Channel layer handler for chat.message events."""
        await self._chat_handler.handle_chat_message(event)

    async def chat_last_open(self, event: dict[str, Any]) -> None:
        """Channel layer handler for chat.last_open events."""
        await self._chat_handler.handle_chat_last_open(event)

    async def my_chats_update(self, event: dict[str, Any]) -> None:
        """Channel layer handler for my_chats.update events."""
        await self._chat_handler.handle_my_chats_update(event)

    async def handle_subscription_results(self, subscription_id: str, result) -> None:
        try:
            async for item in result:
                if subscription_id in self.subscriptions:
                    await self.send_message(
                        "next", subscription_id, {"data": item.data}
                    )
        except Exception as e:
            if subscription_id in self.subscriptions:
                await self.send_message(
                    "error", subscription_id, _safe_error_payload(e)
                )
        finally:
            if subscription_id in self.subscriptions:
                await self.cleanup_subscription(subscription_id)
                await self.send_message("complete", subscription_id)

    async def handle_stop(self, data: dict[str, Any]) -> None:
        subscription_id = data.get("id")
        if subscription_id in self.subscriptions:
            await self.cleanup_subscription(subscription_id)

    async def cleanup_subscription(self, sub_id: str) -> None:
        if sub_id not in self.subscriptions:
            return
        subscription = self.subscriptions.pop(sub_id)

        if not await self._chat_handler.cleanup(sub_id, subscription):
            if hasattr(subscription, "close"):
                await subscription.close()

    async def send_message(
        self,
        message_type: str,
        id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        message = {"type": message_type}
        if id is not None:
            message["id"] = id
        if payload is not None:
            message["payload"] = payload
        logger.debug("Sending WS frame: type=%s id=%s", message_type, id)
        await self.send(text_data=json.dumps(message))

    def get_context(self) -> dict[str, Any]:
        return {
            "request": self.scope,
            "consumer": self,
            "channel": self.channel_name,
        }
