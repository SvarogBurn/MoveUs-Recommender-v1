import graphene
import datetime

from channels.db import database_sync_to_async
from django.db.models.functions.datetime import Now

from main_app.graphql.chat.types import WSChatMessageType, WSLastOpenType
from main_app.models import ChatMessage, ChatMember
from main_app.util import get_chat_member, wait_for_chat_event, notifiy_chat_event, ChatEventType

@database_sync_to_async
def get_chat_messages(chat_id: int, last_update: datetime.datetime):
    return list(ChatMessage.objects.filter(
                chat_id=chat_id,
                time_sent__gt=last_update
            ).values('id', 'time_sent', 'text_content', 'user_id'))

@database_sync_to_async
def get_chat_member_async(chat_id: int, user_id: int):
    return get_chat_member(chat_id, user_id)

@database_sync_to_async
def update_last_open(chat_member: ChatMember):
    chat_member.last_open = Now()
    chat_member.save()

@database_sync_to_async
def get_last_open(chat_id: int, user_id: int, last_update: datetime.datetime) -> list[WSLastOpenType]:
    return [WSLastOpenType(
        user_id=member['user_id'],
        last_open =member['last_open'],
    ) for member in ChatMember.objects.filter(
                chat_id=chat_id,
                last_open__gt=last_update
            ).exclude(
                user_id=user_id
            ).values('user_id', 'last_open')]

class Subscription(graphene.ObjectType):
    chat_messages = graphene.List(
        WSChatMessageType, 
        chat_id=graphene.Int(required=True)
        )
    
    chat_last_open = graphene.List(
        WSLastOpenType, 
        chat_id=graphene.Int(required=True)
        )

    async def subscribe_chat_messages(root, info, chat_id: int):
        chat_member = await get_chat_member_async(chat_id, info.context['request']['user_id'])
        last_update = datetime.datetime(1, 1, 1, 0, 0)

        while True:
            messages = await get_chat_messages(chat_id, last_update)
            if messages:
                yield [
                    WSChatMessageType(
                        id=message['id'],
                        user_id=message['user_id'],
                        time_sent=message['time_sent'],
                        text_content=message['text_content']
                    ) for message in messages
                ]
                last_update = datetime.datetime.now()
                await update_last_open(chat_member)
                notifiy_chat_event(ChatEventType.LastOpenEvent, chat_id)
            await wait_for_chat_event(ChatEventType.MessageEvent, chat_id)

    async def subscribe_chat_last_open(root, info, chat_id: int):
        user_id = info.context['request']['user_id']
        await get_chat_member_async(chat_id, user_id)
        last_update = datetime.datetime(1, 1, 1, 0, 0)

        while True:
            last_open = await get_last_open(chat_id, user_id, last_update)
            if last_open:
                yield last_open
                last_update = datetime.datetime.now()
            await wait_for_chat_event(ChatEventType.LastOpenEvent, chat_id)

