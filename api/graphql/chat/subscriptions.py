import graphene

from api.graphql.chat.types import (
    WSChatMessageType,
    WSLastOpenType,
    WSMyChatUpdateType,
)


class Subscription(graphene.ObjectType):
    chat_messages = graphene.List(
        WSChatMessageType,
        chat_id=graphene.Int(required=True),
    )

    chat_last_open = graphene.List(
        WSLastOpenType,
        chat_id=graphene.Int(required=True),
    )

    my_chats = graphene.List(WSMyChatUpdateType)
