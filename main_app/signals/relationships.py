from django.db.models.functions import Now
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from ..models import Chat, ChatMember, Relationship


@receiver(post_save, sender=Relationship, dispatch_uid="main_app.signals.update_relationship_update_time")
def update_relationship_update_time_handler(sender, instance: Relationship, **kwargs):
    
    if instance.pk is None:
        return

    prev = sender.objects.get(pk = instance.pk)
    if prev.status != instance.status:
        instance.last_update = Now()
        instance.save()

@receiver(post_save, sender=Relationship, dispatch_uid="main_app.signals.create_relationship_chat")
def create_relationship_chat(sender, instance: Relationship, **kwargs):
    
    if 'created' in kwargs:
        if kwargs['created']:

            chat = Chat.objects.create();
            ChatMember.objects.create(user = instance.user_1,
                                            chat = chat, 
                                            nickname = instance.user_1.username)
            ChatMember.objects.create(user = instance.user_2,
                                            chat = chat, 
                                            nickname = instance.user_2.username)
            instance.chat = chat
            instance.save()