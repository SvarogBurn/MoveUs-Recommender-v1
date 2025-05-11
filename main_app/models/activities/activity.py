from django.db import models

from ..enums import ActivityEnum


class Activity(models.Model):
    id = models.SmallIntegerField (
        choices = ActivityEnum.choices(),
        primary_key = True
    )