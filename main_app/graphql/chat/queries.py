import graphene

from main_app.graphql.chat.types import ChatType
from main_app.graphql.error import MUError, MUErrorCode
from main_app.models import Chat, ChatMember
from main_app.util import require_auth


class MyChatsQuery(graphene.ObjectType):
    my_chats = graphene.List(ChatType)
    chat = graphene.Field(
        ChatType,
        chat_id = graphene.Int(required=True)
        )
    
    @require_auth
    def resolve_my_chats(self, info):
        return Chat.objects.filter(
            id__in = ChatMember.objects.filter(
                user_id = info.context.user.id
            ).values('chat_id')
        )
    
    @require_auth
    def resolve_chat(self, info, chat_id: int):
        try:
            return Chat.objects.filter(
                id = chat_id,
                id__in = ChatMember.objects.filter(
                    user_id = info.context.user.id
                ).values('chat_id')
            )[0]
        except IndexError:
            raise MUError(MUErrorCode.CHAT_DOES_NOT_EXIST)