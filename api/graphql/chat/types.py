import graphene

from api.graphql.object_type import MUObjectType
from main.chat.models import Chat, ChatMember, ChatMessage
from shared.enums import ChatNotifications
from shared.utils.decorators import require_auth
from shared.storage import storage_backend


class ChatMemberType(MUObjectType):
    notifications = graphene.Field(ChatNotifications.as_graphene_enum())

    class Meta:
        model = ChatMember
        fields = ("user", "nickname", "chat", "last_open", "notifications")

    def resolve_notifications(self: ChatMember, info: graphene.ResolveInfo) -> int:
        return self.notifications


class ChatMessageType(MUObjectType):
    attachment_url = graphene.String()

    class Meta:
        model = ChatMessage
        fields = ("id", "user", "text_content", "time_sent")

    def resolve_attachment_url(
        self: ChatMessage, info: graphene.ResolveInfo
    ) -> str | None:
        if self.attachment:
            return storage_backend.generate_attachment_url(self.attachment)


class WSChatMessageType(graphene.ObjectType):
    id = graphene.Int()
    time_sent = graphene.DateTime()
    user_id = graphene.Int()
    text_content = graphene.String()
    attachment_url = graphene.String()


class WSLastOpenType(graphene.ObjectType):
    user_id = graphene.Int()
    last_open = graphene.DateTime()


class ChatType(MUObjectType):
    notifications = ChatNotifications.as_graphene_enum()()
    last_message = graphene.Field(ChatMessageType)
    members = graphene.List(ChatMemberType, required=True)

    class Meta:
        model = Chat
        fields = ("id", "time_created", "members", "messages")

    @require_auth
    def resolve_notifications(self: Chat, info: graphene.ResolveInfo) -> int:
        return ChatMember.objects.get(
            chat_id=self.id, user_id=info.context.user.id
        ).notifications

    @require_auth
    def resolve_last_message(
        self: Chat, info: graphene.ResolveInfo
    ) -> ChatMessage | None:
        try:
            return ChatMessage.objects.filter(chat_id=self.id).latest("time_sent")
        except ChatMessage.DoesNotExist:
            return None

    @require_auth
    def resolve_members(self: Chat, info: graphene.ResolveInfo):
        return (
            ChatMember.objects.select_related("user")
            .filter(
                chat_id=self.id,
            )
            .exclude(user_id=info.context.user.id)
        )
