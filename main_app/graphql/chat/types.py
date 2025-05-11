import graphene

from ..object_type import MUObjectType

from ...models import Chat, ChatMember, ChatMessage
from main_app.util import require_auth, generate_attachment_url
from main_app.models.enums import ChatNotifications

class ChatMemberType(MUObjectType):
    class Meta:
        model = ChatMember
        fields = ('user', 'nickname', 'last_open')

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

    class Meta:
        model = Chat
        exclude = ('relationship_set', 'event_set')

    @require_auth
    def resolve_notifications(self: Chat, info):
        return ChatMember.objects.get(
            chat_id = self.id,
            user_id = info.context.user.id
        ).notifications