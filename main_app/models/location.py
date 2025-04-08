from django.db import models

from .enums import CountryCode

class Location(models.Model):
    longitude = models.FloatField()
    latitude = models.FloatField()
    address_line_1 = models.CharField(max_length=64, null=True)
    address_line_2 = models.CharField(max_length=64, null=True)
    zip_code = models.IntegerField(null=True)
    country_code = models.CharField(choices = CountryCode.choices(), null=True)
    region = models.CharField(max_length=32, null=True)
    name = models.CharField(max_length=32, null=True)

