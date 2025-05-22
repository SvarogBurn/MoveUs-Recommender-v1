import graphene

from django.db.models import Q

from main_app.graphql.chat.types import ChatType
from main_app.graphql.error import MUError, MUErrorCode
from main_app.models import Chat, ChatMember, User, Relationship
from main_app.models.enums import RelationshipStatus
from main_app.util import require_auth


class MyChatsQuery(graphene.ObjectType):
    my_chats = graphene.List(ChatType)
    chat = graphene.Field(
        ChatType,
        chat_id = graphene.Int(required=True)
        )
    user_chat = graphene.Field(
        ChatType,
        user_id = graphene.Int()
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
        
    @require_auth
    def resolve_user_chat(self, info, user_id: int):
        if user_id == info.context.user.id:
            raise MUError(MUErrorCode.CANNOT_MESSAGE_YOURSELF)

        target_user: User
        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return MUError(MUErrorCode.USER_DOES_NOT_EXIST)
        
        relationship: Relationship
        try:
            q1 = Q(user_1 = info.context.user, user_2 = target_user)
            q2 = Q(user_2 = info.context.user, user_1 = target_user)
            relationship = Relationship.objects.get(
                q1 | q2
            )
        except Relationship.DoesNotExist:
            relationship = Relationship.objects.create(
                user_1 = info.context.user,
                user_2 = target_user,
                status = RelationshipStatus.NONE
            )
            relationship.refresh_from_db()
        
        return relationship.chat
        