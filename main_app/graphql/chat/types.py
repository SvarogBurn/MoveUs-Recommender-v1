import graphene

from main_app.models.enums import ChatNotifications
from main_app.util import generate_attachment_url, require_auth

from ...models import Chat, ChatMember, ChatMessage
from ..object_type import MUObjectType


class ChatMemberType(MUObjectType):
    notifications = graphene.Field(ChatNotifications.as_graphene_enum())

    class Meta:
        model = ChatMember
        fields = ('user', 'nickname', 'chat', 'last_open', 'notifications')

    def resolve_notifications(self: ChatMember, info):
        return self.notifications

class ChatMessageType(MUObjectType):
    attachment_url = graphene.String()

    class Meta:
        model = ChatMessage
        fields = ('id', 'user', 'text_content', 'time_sent'
        '')

    def resolve_attachment_url(self: ChatMessage, info):
        if self.attachment:
            return generate_attachment_url(self.attachment)

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
        fields = ('id', 'time_created', 'members', 'messages')

    @require_auth
    def resolve_notifications(self: Chat, info):
        return ChatMember.objects.get(
            chat_id = self.id,
            user_id = info.context.user.id
        ).notifications
    
    @require_auth
    def resolve_last_message(self: Chat, info):
        try:
            return ChatMessage.objects.filter(
                chat_id = self.id
            ).latest('time_sent')
        except ChatMessage.DoesNotExist:
            return None
        
    @require_auth
    def resolve_members(self: Chat, info):
        return ChatMember.objects.filter(
            chat_id = self.id,
        ).exclude(
            user_id = info.context.user.id
        )