from django.db import models
from polymorphic.models import PolymorphicModel

class Activity(PolymorphicModel):
    name = models.CharField(max_length=32)