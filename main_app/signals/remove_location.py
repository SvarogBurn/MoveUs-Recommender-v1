from django.db.models.signals import pre_delete
from django.dispatch import receiver
from ..models import Event, Location

# removes unused locations

@receiver(pre_delete, sender=Event, dispatch_uid="main_app.signals.remove_event_location_handler")
def remove_event_location_handler(sender, instance: Event, **kwargs):
    location: Location = instance.location;
    location.consider_dying()

