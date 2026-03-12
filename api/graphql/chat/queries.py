import graphene
from django.db.models import Prefetch

from api.graphql.chat.types import ChatType
from main.chat.models import Chat, ChatMember
from main.social.services import RelationshipService
from main.user.models import User
from shared.errors.mu_error import MUError, MUErrorCode
from shared.utils.decorators import require_auth

_MEMBERS_PREFETCH = Prefetch("members", to_attr="_members")


class MyChatsQuery(graphene.ObjectType):
    my_chats = graphene.List(ChatType)
    chat = graphene.Field(ChatType, chat_id=graphene.Int(required=True))
    user_chat = graphene.Field(ChatType, user_id=graphene.Int())

    @require_auth
    def resolve_my_chats(self, info: graphene.ResolveInfo):
        return Chat.objects.filter(
            id__in=ChatMember.objects.filter(user_id=info.context.user.id).values(
                "chat_id"
            )
        ).prefetch_related(_MEMBERS_PREFETCH)

    @require_auth
    def resolve_chat(self, info: graphene.ResolveInfo, chat_id: int) -> Chat:
        try:
            return Chat.objects.filter(
                id=chat_id,
                id__in=ChatMember.objects.filter(user_id=info.context.user.id).values(
                    "chat_id"
                ),
            ).prefetch_related(_MEMBERS_PREFETCH)[0]
        except IndexError:
            raise MUError(MUErrorCode.CHAT_DOES_NOT_EXIST)

    @require_auth
    def resolve_user_chat(self, info: graphene.ResolveInfo, user_id: int):
        if user_id == info.context.user.id:
            raise MUError(MUErrorCode.CANNOT_MESSAGE_YOURSELF)

        try:
            target_user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

        relationship = RelationshipService.get_or_create_relationship(
            info.context.user, target_user
        )
        return relationship.chat
