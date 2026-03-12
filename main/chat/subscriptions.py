import datetime
import logging
from typing import TYPE_CHECKING, Any

from main.chat.services import ChatService, last_open_group, messages_group

if TYPE_CHECKING:
    from core.consumers import GraphQLSubscriptionConsumer

logger = logging.getLogger(__name__)


class ChatSubscriptionHandler:

    def __init__(self, consumer: "GraphQLSubscriptionConsumer") -> None:
        self.consumer = consumer
        self.chat_groups: dict[str, set[str]] = {}

    async def start_chat_messages(self, sub_id: str, chat_id: int) -> None:
        user_id = self.consumer.scope["user_id"]
        try:
            chat_member = await ChatService.get_chat_member_async(chat_id, user_id)
        except Exception as e:
            await self.consumer.send_message("error", sub_id, {"message": str(e)})
            return

        group = messages_group(chat_id)
        self.consumer.subscriptions[sub_id] = {
            "type": "chat_messages",
            "chat_id": chat_id,
            "group": group,
        }

        # Join BEFORE querying to avoid missing messages
        await self.consumer.channel_layer.group_add(group, self.consumer.channel_name)
        self.chat_groups.setdefault(group, set()).add(sub_id)
        logger.debug(
            "User %s joined group %s for chat %s", user_id, group, chat_id
        )

        # Send initial messages
        since = datetime.datetime(1, 1, 1, tzinfo=datetime.timezone.utc)
        messages = await ChatService.get_initial_messages(chat_id, since)
        if messages:
            await self.consumer.send_message(
                "next", sub_id, {"data": {"chatMessages": messages}}
            )

        # Update last_open and broadcast
        last_open = await ChatService.update_member_last_open(chat_member)
        await self.consumer.channel_layer.group_send(
            last_open_group(chat_id),
            {
                "type": "chat.last_open",
                "user_id": int(user_id),
                "last_open": str(last_open),
            },
        )

    async def start_chat_last_open(self, sub_id: str, chat_id: int) -> None:
        user_id = self.consumer.scope["user_id"]
        try:
            await ChatService.get_chat_member_async(chat_id, user_id)
        except Exception as e:
            await self.consumer.send_message("error", sub_id, {"message": str(e)})
            return

        group = last_open_group(chat_id)
        self.consumer.subscriptions[sub_id] = {
            "type": "chat_last_open",
            "chat_id": chat_id,
            "group": group,
        }

        await self.consumer.channel_layer.group_add(group, self.consumer.channel_name)
        self.chat_groups.setdefault(group, set()).add(sub_id)

        # Send initial last_open data
        since = datetime.datetime(1, 1, 1, tzinfo=datetime.timezone.utc)
        last_open_data = await ChatService.get_last_open_updates(
            chat_id, int(user_id), since
        )
        if last_open_data:
            await self.consumer.send_message(
                "next", sub_id, {"data": {"chatLastOpen": last_open_data}}
            )

    async def handle_chat_message(self, event: dict[str, Any]) -> None:
        logger.debug("Received channel layer chat.message event: %s", event)
        for grp, sub_ids in self.chat_groups.items():
            if not grp.endswith("_messages"):
                continue
            for sub_id in list(sub_ids):
                sub = self.consumer.subscriptions.get(sub_id)
                if not sub:
                    continue
                data = {
                    k: event[k]
                    for k in (
                        "id",
                        "userId",
                        "textContent",
                        "timeSent",
                        "attachmentUrl",
                    )
                }
                await self.consumer.send_message(
                    "next", sub_id, {"data": {"chatMessages": [data]}}
                )

                # Update last_open for this user
                chat_id = sub["chat_id"]
                user_id = self.consumer.scope["user_id"]
                try:
                    chat_member = await ChatService.get_chat_member_async(
                        chat_id, user_id
                    )
                    last_open = await ChatService.update_member_last_open(chat_member)
                    await self.consumer.channel_layer.group_send(
                        last_open_group(chat_id),
                        {
                            "type": "chat.last_open",
                            "user_id": int(user_id),
                            "last_open": str(last_open),
                        },
                    )
                except Exception:
                    pass

    async def handle_chat_last_open(self, event: dict[str, Any]) -> None:
        data = {
            "userId": event["user_id"],
            "lastOpen": event["last_open"],
        }
        for grp, sub_ids in self.chat_groups.items():
            if not grp.endswith("_last_open"):
                continue
            for sub_id in list(sub_ids):
                if sub_id in self.consumer.subscriptions:
                    await self.consumer.send_message(
                        "next", sub_id, {"data": {"chatLastOpen": [data]}}
                    )

    async def cleanup(self, sub_id: str, subscription: dict[str, Any]) -> bool:
        if not isinstance(subscription, dict) or "group" not in subscription:
            return False
        group = subscription["group"]
        if group in self.chat_groups:
            self.chat_groups[group].discard(sub_id)
            if not self.chat_groups[group]:
                del self.chat_groups[group]
                await self.consumer.channel_layer.group_discard(
                    group, self.consumer.channel_name
                )
        return True

    async def disconnect(self) -> None:
        for group in list(self.chat_groups.keys()):
            await self.consumer.channel_layer.group_discard(
                group, self.consumer.channel_name
            )
        self.chat_groups.clear()
