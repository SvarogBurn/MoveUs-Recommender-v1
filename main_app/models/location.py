from django.db import models
from polymorphic.models import PolymorphicModel

class BaseLocation(PolymorphicModel):
    longitude = models.FloatField()
    latitude = models.FloatField()

class AdressLocation(BaseLocation):
    address_line_1 = models.CharField(max_length=64)
    address_line_2 = models.CharField(max_length=64)
    post_code = models.IntegerField()
    country_code = models.CharField(max_length=2)
    region = models.CharField(max_length=32)

class InstituteLocation(AdressLocation):
    name = models.CharField(max_length=32)

