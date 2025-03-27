from django.db.models.signals import post_save
from django.dispatch import receiver
from ..models import MoveusUser, UserPrivacySetting
from ..models.enums import PrivacySetting, PrivacyScope

@receiver(post_save, sender=MoveusUser, dispatch_uid="main_app.signals.add_privacy_settings_handler")
def add_privacy_settings_handler(sender, instance, **kwargs):

    # call only when created
    if 'created' in kwargs:
        if kwargs['created']:

            # add all possible privacy settings to user, and put them all to public
            for key in PrivacySetting:
                ups = UserPrivacySetting.objects.create(
                        user = instance,
                        setting = key.value,
                        scope = PrivacyScope.EVERYONE
                    )
                ups.save()
