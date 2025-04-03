from django.db import models
from polymorphic.models import PolymorphicModel

from .activity_enum import ActivityEnum

class Activity(PolymorphicModel):
    id = models.SmallIntegerField (
        choices = ActivityEnum.choices(),
        primary_key = True
    )
    has_ballz = models.BooleanField(default=False)