from django.db import models
from django.db.models.fields.composite import CompositePrimaryKey

from .enums import PrivacySetting as PS, PrivacyScope, OtherOption as OO, PersonalityTrait as PT

class UserPersonalityTrait(models.Model):
    pk = CompositePrimaryKey('user', 'trait')
    user = models.ForeignKey("User", on_delete=models.CASCADE, )
    trait = models.SmallIntegerField(choices=PT.choices())
    factor = models.FloatField()

class UserPrivacySetting(models.Model):
    pk = CompositePrimaryKey('user', 'setting')
    user = models.ForeignKey("User", on_delete=models.CASCADE, related_name='privacy_settings')
    setting = models.SmallIntegerField(choices=PS.choices())
    scope = models.SmallIntegerField(choices=PrivacyScope.choices(), default=PrivacyScope.EVERYONE)

class UserOtherOption(models.Model):
    pk = CompositePrimaryKey('user', 'option')
    user = models.ForeignKey("User", on_delete=models.CASCADE)
    option = models.SmallIntegerField(choices=OO.choices())
    text = models.CharField(max_length=128)

class UserReport(models.Model):
    reporter = models.ForeignKey("User", on_delete=models.CASCADE)
    reported = models.ForeignKey("User", on_delete=models.CASCADE, related_name='reported_by')
    comment = models.CharField(max_length=256)

class EventReport(models.Model):
    reporter = models.ForeignKey("User", on_delete=models.CASCADE)
    reported = models.ForeignKey("Event", on_delete=models.CASCADE, related_name='reported_by')
    comment = models.CharField(max_length=256)