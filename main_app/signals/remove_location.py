from django.db.models.signals import pre_delete
from django.dispatch import receiver
from ..models import User, Event, Location

# deletes unused locations

@receiver(pre_delete, sender=User, dispatch_uid="main_app.signals.remove_user_location_handler")
def remove_user_location_handler(sender, instance: User, **kwargs):
    location = instance.location;
    used_by_count = location.user_set.count() + location.event_set.count()
    if used_by_count == 1:
        location.delete()

@receiver(pre_delete, sender=Event, dispatch_uid="main_app.signals.remove_event_location_handler")
def remove_event_location_handler(sender, instance: Event, **kwargs):
    location = instance.location;
    used_by_count = location.user_set.count() + location.event_set.count()
    if used_by_count == 1:
        location.delete()

