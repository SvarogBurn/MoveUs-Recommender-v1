from django.db.models.signals import post_save
from django.dispatch import receiver

from ..models import Chat, Event


@receiver(post_save, sender=Event, dispatch_uid="main_app.signals.create_event_chat")
def create_event_chat(sender, instance: Event, **kwargs):
    
    if 'created' in kwargs:
        if kwargs['created']:

            chat = Chat.objects.create();
            instance.chat = chat
            instance.save()