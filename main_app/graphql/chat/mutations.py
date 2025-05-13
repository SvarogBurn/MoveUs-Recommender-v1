import graphene

from main_app.graphql.error import MUError, MUErrorCode
from main_app.models import ChatMessage
from main_app.models.enums import ChatNotifications
from main_app.util import get_chat_member, require_auth, validate_attachment


class SetChatNotifications(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)
        notifications = ChatNotifications.as_graphene_enum()(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self,
        info,
        chat_id: int,
        notifications: ChatNotifications
    ):
        user_id: int = info.context.user.id
        chatmember = get_chat_member(chat_id, user_id)
        chatmember.notifications = notifications
        chatmember.save()

        return SetChatNotifications(success=True)

class SetChatNickname(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)
        nickname = graphene.String(required=True)

    success = graphene.Boolean()

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
        chatmember = get_chat_member(chat_id, user_id)
        chatmember.nickname = nickname
        chatmember.save()

        return SetChatNickname(success=True)
    
class SendChatMessage(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)
        message = graphene.String(required=True)
        attachment_id = graphene.String(required=False)

    success = graphene.Boolean()

    @require_auth
    def mutate(
        self,
        info,
        chat_id: int,
        message: str,
        attachment_id: str = None
    ):
        if len(message) > 512:
            raise MUError(MUErrorCode.MESSAGE_MAX_LENGTH)

        user_id: int = info.context.user.id
        get_chat_member(chat_id, user_id)

        if attachment_id:
            validate_attachment(attachment_id, user_id)
        
        ChatMessage.objects.create(
            chat_id = chat_id,
            user_id = user_id,
            text_content = message,
            attachment = attachment_id
        )

        return SendChatMessage(success=True)

class Mutation(graphene.ObjectType):
    set_chat_notifications = SetChatNotifications.Field()
    set_chat_nickname = SetChatNickname.Field()
    send_chat_message = SendChatMessage.Field()