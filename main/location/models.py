from django.db import models

from shared.enums import CountryCode


class Location(models.Model):
    longitude = models.FloatField()
    latitude = models.FloatField()
    address_line_1 = models.CharField(max_length=64, null=True)
    address_line_2 = models.CharField(max_length=64, null=True)
    zip_code = models.IntegerField(null=True)
    country_code = models.CharField(choices=CountryCode.choices(), null=True)
    region = models.CharField(max_length=32, null=True)
    name = models.CharField(max_length=32, null=True)
    city = models.CharField(max_length=32, null=True)

    class Meta:
        db_table = "main_app_location"

    def reference_count(self) -> int:
        from main.event.models import Event

        return Event.objects.filter(location=self).count()

    def consider_dying(self) -> None:
        if self.reference_count() <= 1:
            self.delete()
