import graphene

from api.graphql.object_type import MUObjectType
from main.chat.models import Chat, ChatMember, ChatMessage, DirectChat, GroupChat
from main.chat.services import ChatMemberService, ChatService
from shared.enums import ChatKind, ChatMessageKind, ChatNotifications
from shared.storage import storage_backend
from shared.utils.decorators import require_auth


class ChatMemberType(MUObjectType):
    notifications = graphene.Field(ChatNotifications.as_graphene_enum())

    class Meta:
        model = ChatMember
        fields = ("user", "nickname", "chat", "last_open", "notifications")

    def resolve_notifications(self: ChatMember, info: graphene.ResolveInfo) -> int:
        return self.notifications


class ChatMessageType(MUObjectType):
    attachment_url = graphene.String()
    kind = graphene.Field(ChatMessageKind.as_graphene_enum())

    class Meta:
        model = ChatMessage
        fields = ("id", "user", "kind", "target_user", "text_content", "time_sent")

    def resolve_kind(self: ChatMessage, info: graphene.ResolveInfo) -> int:
        return self.kind

    def resolve_attachment_url(
        self: ChatMessage, info: graphene.ResolveInfo
    ) -> str | None:
        if self.attachment:
            return storage_backend.generate_attachment_url(self.attachment)


class WSChatMessageType(graphene.ObjectType):
    id = graphene.Int()
    time_sent = graphene.DateTime()
    user_id = graphene.Int()
    kind = graphene.String()
    target_user_id = graphene.Int()
    text_content = graphene.String()
    attachment_url = graphene.String()


class WSLastOpenType(graphene.ObjectType):
    user_id = graphene.Int()
    last_open = graphene.DateTime()


class WSChatMemberType(graphene.ObjectType):
    user_id = graphene.Int()
    username = graphene.String()
    first_name = graphene.String()
    last_name = graphene.String()
    nickname = graphene.String()
    last_open = graphene.DateTime()


class WSChatType(graphene.ObjectType):
    id = graphene.Int()
    time_created = graphene.DateTime()
    kind = graphene.String()
    group_name = graphene.String()
    members = graphene.List(WSChatMemberType)
    last_message = graphene.Field(WSChatMessageType)


class WSMyChatUpdateType(graphene.ObjectType):
    event_type = graphene.String()
    chat_id = graphene.Int()
    last_message = graphene.Field(WSChatMessageType)
    chat = graphene.Field(WSChatType)
    member = graphene.Field(WSChatMemberType)
    removed_user_id = graphene.Int()


class ChatType(MUObjectType):
    kind = graphene.Field(ChatKind.as_graphene_enum())
    group_name = graphene.String()
    notifications = ChatNotifications.as_graphene_enum()()
    last_message = graphene.Field(ChatMessageType)
    members = graphene.List(
        ChatMemberType,
        required=True,
        include_former=graphene.Boolean(required=False, default_value=False),
    )

    class Meta:
        model = Chat
        fields = ("id", "time_created", "members", "messages")

    def resolve_kind(self: Chat, info: graphene.ResolveInfo) -> int:
        return ChatService.get_chat_kind(self.id)

    def resolve_group_name(self: Chat, info: graphene.ResolveInfo) -> str | None:
        try:
            return self.group_chat.name
        except GroupChat.DoesNotExist:
            return None

    @require_auth
    def resolve_notifications(self: Chat, info: graphene.ResolveInfo) -> int:
        return ChatMemberService.get_notifications_setting(
            self.id, info.context.user.id
        )

    @require_auth
    def resolve_last_message(
        self: Chat, info: graphene.ResolveInfo
    ) -> ChatMessage | None:
        return ChatService.get_last_message(self.id)

    def resolve_members(
        self: Chat, info: graphene.ResolveInfo, include_former: bool = False
    ):
        return ChatMemberService.get_members(self.id, include_former=include_former)
