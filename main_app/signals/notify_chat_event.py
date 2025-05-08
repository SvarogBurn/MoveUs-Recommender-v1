from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import ChatMessage
from main_app.util import notifiy_chat_event, ChatEventType

@receiver(post_save, sender=ChatMessage, dispatch_uid="main_app.signals.notify_chat_event")
def notify_chat_event_handler(sender, instance: ChatMessage, **kwargs):

    if 'created' in kwargs:
        if kwargs['created']:
            notifiy_chat_event(ChatEventType.MessageEvent, instance.chat.id)
