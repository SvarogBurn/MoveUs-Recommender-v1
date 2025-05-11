from django.db.models.signals import post_delete
from django.dispatch import receiver

from ..models import Event, Notification, User


@receiver(post_delete, sender=Event, dispatch_uid="main_app.signals.remove_target_event_notification")
def remove_target_event_notification_handler(sender, instance: Event, **kwargs):
    
    Notification.objects.delete(
        target_id = sender.id,
        type__in = Notification.EVENT_NOTIFICATION_TYPES
    )

@receiver(post_delete, sender=User, dispatch_uid="main_app.signals.remove_target_user_notification")
def remove_target_user_notification_handler(sender, instance: User, **kwargs):
    
    Notification.objects.delete(
        target_id = sender.id,
        type__in = Notification.USER_NOTIFICATION_TYPES
    )
