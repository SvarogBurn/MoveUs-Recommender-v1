import graphene

from api.graphql.chat.types import ChatMemberType, ChatMessageType
from main.chat.services import ChatService
from main.chat.validators import validate_message, validate_nickname
from shared.enums import ChatNotifications
from shared.storage import storage_backend
from shared.utils.decorators import require_auth


class SetChatNotifications(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)
        notifications = ChatNotifications.as_graphene_enum()(required=True)

    chat_member = graphene.Field(ChatMemberType)

    @require_auth
    def mutate(
        self, info: graphene.ResolveInfo, chat_id: int, notifications: ChatNotifications
    ):
        user_id: int = info.context.user.id
        member = ChatService.get_chat_member(chat_id, user_id)
        member.notifications = notifications
        member.save()

        return SetChatNotifications(chat_member=member)


class SetChatNickname(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)
        nickname = graphene.String(required=True)

    chat_member = graphene.Field(ChatMemberType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, chat_id: int, nickname: str):
        validate_nickname(nickname)

        user_id: int = info.context.user.id
        member = ChatService.get_chat_member(chat_id, user_id)
        member.nickname = nickname
        member.save()

        return SetChatNickname(chat_member=member)


class SendChatMessage(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)
        message = graphene.String(required=False)
        attachment_id = graphene.String(required=False)

    chat_message = graphene.Field(ChatMessageType)

    @require_auth
    def mutate(
        self,
        info: graphene.ResolveInfo,
        chat_id: int,
        message: str = None,
        attachment_id: str = None,
    ):

        validate_message(message, attachment_id)

        user_id: int = info.context.user.id
        ChatService.get_chat_member(chat_id, user_id)

        if attachment_id:
            storage_backend.validate_attachment(attachment_id, user_id)

        msg = ChatService.send_message(chat_id, user_id, message, attachment_id)

        return SendChatMessage(chat_message=msg)


class Mutation(graphene.ObjectType):
    set_chat_notifications = SetChatNotifications.Field()
    set_chat_nickname = SetChatNickname.Field()
    send_chat_message = SendChatMessage.Field()
