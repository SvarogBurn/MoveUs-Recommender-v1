import graphene

from api.graphql.chat.types import ChatMemberType, ChatMessageType, ChatType
from main.chat.models import Chat, ChatMember
from main.chat.services import ChatMemberService, ChatService
from main.chat.validators import validate_message, validate_nickname
from main.user.models import User
from shared.enums import ChatNotifications
from shared.errors.mu_error import MUError, MUErrorCode
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
        member = ChatMemberService.get_chat_member(chat_id, user_id)
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
        member = ChatMemberService.get_chat_member(chat_id, user_id)
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
        ChatMemberService.get_chat_member(chat_id, user_id)

        if attachment_id:
            storage_backend.validate_attachment(attachment_id, user_id)

        msg = ChatService.send_message(chat_id, user_id, message, attachment_id)

        return SendChatMessage(chat_message=msg)


class CreateGroupChat(graphene.Mutation):

    class Arguments:
        user_ids = graphene.List(graphene.Int, required=True)

    chat = graphene.Field(ChatType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, user_ids: list[int]):
        chat = ChatService.create_group_chat(info.context.user, user_ids)
        return CreateGroupChat(chat=chat)


class AddChatMember(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)
        user_id = graphene.Int(required=True)

    chat = graphene.Field(ChatType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, chat_id: int, user_id: int):
        try:
            chat = Chat.objects.get(pk=chat_id)
        except Chat.DoesNotExist:
            raise MUError(MUErrorCode.CHAT_DOES_NOT_EXIST)

        ChatMemberService.get_chat_member(chat_id, info.context.user.id)

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise MUError(MUErrorCode.USER_DOES_NOT_EXIST)

        ChatMemberService.add_chat_member(chat, user)
        return AddChatMember(chat=chat)


class LeaveChat(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, chat_id: int):
        ChatMemberService.get_chat_member(chat_id, info.context.user.id)
        ChatMemberService.remove_chat_member(chat_id, info.context.user.id)
        return LeaveChat(success=True)


class Mutation(graphene.ObjectType):
    set_chat_notifications = SetChatNotifications.Field()
    set_chat_nickname = SetChatNickname.Field()
    send_chat_message = SendChatMessage.Field()
    create_group_chat = CreateGroupChat.Field()
    add_chat_member = AddChatMember.Field()
    leave_chat = LeaveChat.Field()
