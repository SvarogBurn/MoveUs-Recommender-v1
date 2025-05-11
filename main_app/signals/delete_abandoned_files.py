from django.db.models.signals import post_delete
from django.dispatch import receiver
from google.api_core.exceptions import NotFound

from core.gcs_client import bucket

from ..models import ChatMessage, Event, Post, User


@receiver(post_delete, sender=User, dispatch_uid="main_app.signals.delete_profile_picture")
def delete_profile_picture_handler(sender, instance: User, **kwargs):
    
    blob = bucket.blob(f'profile-pictures/{instance.id}')
    try:
        blob.delete()
    except NotFound:
        pass

@receiver(post_delete, sender=Event, dispatch_uid="main_app.signals.delete_event_picture")
def delete_event_picture_handler(sender, instance: Event, **kwargs):
    
    blob = bucket.blob(f'event-pictures/{instance.id}')
    try:
        blob.delete()
    except NotFound:
        pass

@receiver(post_delete, sender=Post, dispatch_uid="main_app.signals.delete_post_picture")
def delete_post_picture_handler(sender, instance: Post, **kwargs):
    
    blob = bucket.blob(f'post-pictures/{instance.id}')
    try:
        blob.delete()
    except NotFound:
        pass

@receiver(post_delete, sender=ChatMessage, dispatch_uid="main_app.signals.delete_chatmessage_attachment")
def delete_chatmessage_attachment_handler(sender, instance: ChatMessage, **kwargs):
    
    if instance.attachment:
        blob = bucket.blob(f'attachment/{instance.attachment}')
        try:
            blob.delete()
        except NotFound:
            pass