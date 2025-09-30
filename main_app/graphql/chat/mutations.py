import graphene

from main_app.graphql.chat.types import ChatMemberType, ChatMessageType
from main_app.graphql.error import MUError, MUErrorCode
from main_app.models import ChatMessage
from main_app.models.enums import ChatNotifications
from main_app.util import get_chat_member, require_auth, validate_attachment


class SetChatNotifications(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)
        notifications = ChatNotifications.as_graphene_enum()(required=True)

    chat_member = graphene.Field(ChatMemberType)

    @require_auth
    def mutate(
        self,
        info,
        chat_id: int,
        notifications: ChatNotifications
    ):
        user_id: int = info.context.user.id
        member = get_chat_member(chat_id, user_id)
        member.notifications = notifications
        member.save()

        return SetChatNotifications(chat_member = member)

class SetChatNickname(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)
        nickname = graphene.String(required=True)

    chat_member = graphene.Field(ChatMemberType)

    @require_auth
    def mutate(
        self,
        info,
        chat_id: int,
        nickname: str
    ):
        if len(nickname) > 24:
            raise MUError(MUErrorCode.NICKNAME_MAX_LENGTH)

        user_id: int = info.context.user.id
        member = get_chat_member(chat_id, user_id)
        member.nickname = nickname
        member.save()

        return SetChatNickname(chat_member = member)
    
class SendChatMessage(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)
        message = graphene.String(required=False)
        attachment_id = graphene.String(required=False)

    chat_message = graphene.Field(ChatMessageType)

    @require_auth
    def mutate(
        self,
        info,
        chat_id: int,
        message: str = None,
        attachment_id: str = None
    ):
        
        if message is None and attachment_id is None:
            raise MUError(MUErrorCode.NO_TEXT_OR_ATTACHMENT)

        if len(message) > 512:
            raise MUError(MUErrorCode.MESSAGE_MAX_LENGTH)

        user_id: int = info.context.user.id
        get_chat_member(chat_id, user_id)

        if attachment_id:
            validate_attachment(attachment_id, user_id)
        
        message = ChatMessage.objects.create(
            chat_id = chat_id,
            user_id = user_id,
            text_content = message,
            attachment = attachment_id
        )

        return SendChatMessage(chat_message = message)

class Mutation(graphene.ObjectType):
    set_chat_notifications = SetChatNotifications.Field()
    set_chat_nickname = SetChatNickname.Field()
    send_chat_message = SendChatMessage.Field()