import datetime
from typing import Any

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.db.models.functions import Now

from main.chat.models import Chat, ChatMember, ChatMessage, DirectChat, GroupChat
from main.user.models import User
from shared.errors.mu_error import MUError, MUErrorCode
from shared.storage import storage_backend


def messages_group(chat_id: int) -> str:
    return f"chat_{chat_id}_messages"


def last_open_group(chat_id: int) -> str:
    return f"chat_{chat_id}_last_open"


def my_chats_group(user_id: int) -> str:
    return f"user_{user_id}_my_chats"


def serialize_message(
    msg_id: int,
    user_id: int,
    text_content: str,
    time_sent: datetime.datetime,
    attachment: str | None = None,
) -> dict[str, Any]:
    return {
        "id": msg_id,
        "userId": user_id,
        "textContent": text_content,
        "timeSent": str(time_sent),
        "attachmentUrl": storage_backend.generate_attachment_url(attachment) if attachment else None,
    }


def notify_my_chats_update(
    chat_id: int, event_type: str, extra_data: dict[str, Any] | None = None
) -> None:
    channel_layer = get_channel_layer()
    member_user_ids = ChatMember.objects.filter(chat_id=chat_id).values_list(
        "user_id", flat=True
    )
    payload = {
        "type": "my_chats.update",
        "event_type": event_type,
        "chat_id": chat_id,
        **(extra_data or {}),
    }
    for uid in member_user_ids:
        async_to_sync(channel_layer.group_send)(my_chats_group(uid), payload)


def _notify_single_user_my_chats(
    user_id: int, chat_id: int, event_type: str, extra_data: dict[str, Any] | None = None
) -> None:
    channel_layer = get_channel_layer()
    payload = {
        "type": "my_chats.update",
        "event_type": event_type,
        "chat_id": chat_id,
        **(extra_data or {}),
    }
    async_to_sync(channel_layer.group_send)(my_chats_group(user_id), payload)


def _serialize_chat(chat: Chat, exclude_user_id: int | None = None) -> dict[str, Any]:
    members = ChatMember.objects.select_related("user").filter(chat_id=chat.id)
    if exclude_user_id is not None:
        members = members.exclude(user_id=exclude_user_id)
    last_msg = (
        ChatMessage.objects.filter(chat_id=chat.id)
        .order_by("-time_sent")
        .first()
    )
    is_direct = DirectChat.objects.filter(chat_id=chat.id).exists()
    group_chat = None if is_direct else GroupChat.objects.filter(chat_id=chat.id).first()

    return {
        "id": chat.id,
        "timeCreated": str(chat.time_created),
        "kind": "DIRECT" if is_direct else "GROUP",
        "groupName": group_chat.name if group_chat else None,
        "members": [
            {
                "userId": m.user_id,
                "nickname": m.nickname,
                "lastOpen": str(m.last_open) if m.last_open else None,
            }
            for m in members
        ],
        "lastMessage": serialize_message(
            last_msg.id,
            last_msg.user_id,
            last_msg.text_content,
            last_msg.time_sent,
            last_msg.attachment,
        )
        if last_msg
        else None,
    }


class ChatMemberService:
    @staticmethod
    def create_member(user: User, chat: Chat) -> ChatMember:
        return ChatMember.objects.create(
            user=user, chat=chat, nickname=user.display_name
        )

    @staticmethod
    def get_chat_member(chat_id: int, user_id: int) -> ChatMember:
        try:
            return ChatMember.objects.get(user_id=user_id, chat_id=chat_id)
        except ChatMember.DoesNotExist:
            raise MUError(MUErrorCode.NOT_IN_CHAT)

    @staticmethod
    @database_sync_to_async
    def get_chat_member_async(chat_id: int, user_id: int) -> ChatMember:
        return ChatMemberService.get_chat_member(chat_id, user_id)

    @staticmethod
    def add_chat_member(chat: Chat, user: User) -> ChatMember:
        if DirectChat.objects.filter(chat_id=chat.id).exists():
            raise MUError(MUErrorCode.CANNOT_ADD_TO_DIRECT_CHAT)
        member, created = ChatMember.objects.get_or_create(
            user=user,
            chat=chat,
            defaults={"nickname": user.display_name},
        )
        if created:
            chat_data = _serialize_chat(chat)
            _notify_single_user_my_chats(
                user.id, chat.id, "chat_added", {"chat": chat_data}
            )
            notify_my_chats_update(
                chat.id,
                "member_added",
                {"member": {"userId": user.id, "nickname": user.display_name}},
            )
        return member

    @staticmethod
    def remove_chat_member(chat_id: int, user_id: int) -> None:
        if DirectChat.objects.filter(chat_id=chat_id).exists():
            raise MUError(MUErrorCode.CANNOT_LEAVE_DIRECT_CHAT)
        ChatMember.objects.filter(user_id=user_id, chat_id=chat_id).delete()
        _notify_single_user_my_chats(user_id, chat_id, "chat_removed")
        notify_my_chats_update(
            chat_id, "member_removed", {"removed_user_id": user_id}
        )

    @staticmethod
    @database_sync_to_async
    def update_member_last_open(chat_member: ChatMember) -> datetime.datetime:
        chat_member.last_open = Now()
        chat_member.save(update_fields=["last_open"])
        chat_member.refresh_from_db(fields=["last_open"])
        notify_my_chats_update(
            chat_member.chat_id,
            "member_last_open",
            {"member": {"userId": chat_member.user_id, "lastOpen": str(chat_member.last_open)}},
        )
        return chat_member.last_open


class ChatService:
    @staticmethod
    def get_or_create_direct_chat(user: User, other_user: User) -> Chat:
        u1, u2 = (user, other_user) if user.id < other_user.id else (other_user, user)
        try:
            return DirectChat.objects.select_related("chat").get(
                user_1=u1, user_2=u2
            ).chat
        except DirectChat.DoesNotExist:
            chat = Chat.objects.create()
            DirectChat.objects.create(user_1=u1, user_2=u2, chat=chat)
            ChatMemberService.create_member(u1, chat)
            ChatMemberService.create_member(u2, chat)
            chat_data = _serialize_chat(chat)
            _notify_single_user_my_chats(
                u1.id, chat.id, "chat_added", {"chat": chat_data}
            )
            _notify_single_user_my_chats(
                u2.id, chat.id, "chat_added", {"chat": chat_data}
            )
            return chat

    @staticmethod
    def create_group_chat(
        creator: User, user_ids: list[int], name: str = ""
    ) -> Chat:
        users = list(User.objects.filter(id__in=user_ids))
        found_ids = {u.id for u in users}
        for uid in user_ids:
            if uid not in found_ids:
                raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

        chat = Chat.objects.create()
        GroupChat.objects.create(chat=chat, name=name)
        ChatMemberService.create_member(creator, chat)
        for u in users:
            if u.id != creator.id:
                ChatMemberService.create_member(u, chat)

        chat_data = _serialize_chat(chat)
        all_member_ids = [creator.id] + [u.id for u in users if u.id != creator.id]
        for uid in all_member_ids:
            _notify_single_user_my_chats(
                uid, chat.id, "chat_added", {"chat": chat_data}
            )
        return chat

    @staticmethod
    def send_message(
        chat_id: int,
        user_id: int,
        text_content: str,
        attachment: str | None = None,
    ) -> ChatMessage:
        msg = ChatMessage.objects.create(
            chat_id=chat_id,
            user_id=user_id,
            text_content=text_content,
            attachment=attachment,
        )
        channel_layer = get_channel_layer()
        data = serialize_message(
            msg.id, user_id, text_content, msg.time_sent, attachment
        )
        async_to_sync(channel_layer.group_send)(
            messages_group(chat_id),
            {
                "type": "chat.message",
                **data,
            },
        )
        notify_my_chats_update(
            chat_id, "new_message", {"last_message": data}
        )
        return msg

    @staticmethod
    def notify_last_open(
        chat_id: int, user_id: int, last_open: datetime.datetime
    ) -> None:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            last_open_group(chat_id),
            {
                "type": "chat.last_open",
                "user_id": user_id,
                "last_open": str(last_open),
            },
        )

    @staticmethod
    @database_sync_to_async
    def get_initial_messages(
        chat_id: int, since: datetime.datetime
    ) -> list[dict[str, Any]]:
        messages = ChatMessage.objects.filter(
            chat_id=chat_id,
            time_sent__gt=since,
        ).values("id", "time_sent", "text_content", "user_id", "attachment")
        return [
            serialize_message(
                m["id"],
                m["user_id"],
                m["text_content"],
                m["time_sent"],
                m["attachment"],
            )
            for m in messages
        ]

    @staticmethod
    @database_sync_to_async
    def get_last_open_updates(
        chat_id: int, user_id: int, since: datetime.datetime
    ) -> list[dict[str, Any]]:
        members = (
            ChatMember.objects.filter(
                chat_id=chat_id,
                last_open__gt=since,
            )
            .exclude(user_id=user_id)
            .values("user_id", "last_open")
        )
        return [
            {
                "userId": m["user_id"],
                "lastOpen": str(m["last_open"]),
            }
            for m in members
        ]

    @staticmethod
    @database_sync_to_async
    def get_user_chats(user_id: int) -> list[dict[str, Any]]:
        chat_ids = ChatMember.objects.filter(user_id=user_id).values_list(
            "chat_id", flat=True
        )
        chats = Chat.objects.filter(id__in=chat_ids)
        return [_serialize_chat(chat, exclude_user_id=user_id) for chat in chats]
