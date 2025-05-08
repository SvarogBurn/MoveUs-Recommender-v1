import graphene

from main_app.graphql.chat.types import ChatType
from main_app.models import User, Chat, ChatMember
from main_app.util import require_auth

class MyChatsQuery(graphene.ObjectType):
    my_chats = graphene.List(ChatType)
    
    @require_auth
    def resolve_my_chats(self, info):
        return Chat.objects.filter(
            id__in = ChatMember.objects.filter(
                user_id = info.context.user.id
            ).values('chat_id')
        )