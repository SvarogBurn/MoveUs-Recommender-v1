import graphene

from api.graphql.chat.types import ChatMemberType, ChatMessageType, ChatType
from main.chat.services import ChatMemberService, ChatService
from shared.enums import ChatNotifications
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
        ChatMemberService.set_notifications(member, notifications)

        return SetChatNotifications(chat_member=member)


class SetChatNickname(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)
        nickname = graphene.String(required=True)

    chat_member = graphene.Field(ChatMemberType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, chat_id: int, nickname: str):
        user_id: int = info.context.user.id
        member = ChatMemberService.get_chat_member(chat_id, user_id)
        ChatMemberService.set_nickname(member, nickname)

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
        user_id: int = info.context.user.id
        msg = ChatService.send_message(chat_id, user_id, message, attachment_id)

        return SendChatMessage(chat_message=msg)


class CreateGroupChat(graphene.Mutation):

    class Arguments:
        user_ids = graphene.List(graphene.Int, required=True)
        name = graphene.String(required=False, default_value="")

    chat = graphene.Field(ChatType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, user_ids: list[int], name: str = ""):
        chat = ChatService.create_group_chat(info.context.user, user_ids, name=name)
        return CreateGroupChat(chat=chat)


class AddChatMember(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)
        user_id = graphene.Int(required=True)

    chat = graphene.Field(ChatType)

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, chat_id: int, user_id: int):
        chat = ChatMemberService.add_member_to_chat(
            chat_id, info.context.user.id, user_id
        )
        return AddChatMember(chat=chat)


class LeaveChat(graphene.Mutation):

    class Arguments:
        chat_id = graphene.Int(required=True)

    success = graphene.Boolean()

    @require_auth
    def mutate(self, info: graphene.ResolveInfo, chat_id: int):
        ChatMemberService.remove_chat_member(chat_id, info.context.user.id)
        return LeaveChat(success=True)


class Mutation(graphene.ObjectType):
    set_chat_notifications = SetChatNotifications.Field()
    set_chat_nickname = SetChatNickname.Field()
    send_chat_message = SendChatMessage.Field()
    create_group_chat = CreateGroupChat.Field()
    add_chat_member = AddChatMember.Field()
    leave_chat = LeaveChat.Field()
