from django.db.models.signals import post_save
from django.dispatch import receiver

from ..models import User, UserPrivacySetting
from ..models.enums import PrivacyScope, PrivacySetting


@receiver(post_save, sender=User, dispatch_uid="main_app.signals.add_privacy_settings_handler")
def add_privacy_settings_handler(sender, instance, **kwargs):

    if 'created' in kwargs:
        if kwargs['created']:

            for key in PrivacySetting:
                ups = UserPrivacySetting.objects.create(
                        user = instance,
                        setting = key.value,
                        scope = PrivacyScope.EVERYONE
                    )
                ups.save()
