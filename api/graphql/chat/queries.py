import graphene

from api.graphql.chat.types import ChatType
from main.chat.models import Chat
from main.chat.services import ChatService
from shared.utils.decorators import require_auth


class ChatQuery(graphene.ObjectType):
    chat = graphene.Field(ChatType, chat_id=graphene.Int(required=True))
    user_chat = graphene.Field(ChatType, user_id=graphene.Int())

    @require_auth
    def resolve_chat(self, info: graphene.ResolveInfo, chat_id: int) -> Chat:
        return ChatService.get_chat_for_member(chat_id, info.context.user.id)

    @require_auth
    def resolve_user_chat(self, info: graphene.ResolveInfo, user_id: int):
        return ChatService.get_or_create_direct_chat(info.context.user.id, user_id)
