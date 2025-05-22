from django.db import models

from ..enums import Activity


class Activity(models.Model):
    id = models.SmallIntegerField (
        choices = Activity.choices(),
        primary_key = True
    )