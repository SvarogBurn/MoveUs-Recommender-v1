from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import Event, Chat

@receiver(post_save, sender=Event, dispatch_uid="main_app.signals.create_event_chat")
def create_event_chat(sender, instance: Event, **kwargs):
    
    # call only when created
    if 'created' in kwargs:
        if kwargs['created']:

            chat = Chat.objects.create();
            instance.chat = chat
            instance.save()