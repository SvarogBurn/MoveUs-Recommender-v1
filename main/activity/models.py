from django.db import models

from shared.enums import ActivityType


class Activity(models.Model):
    id = models.SmallIntegerField(choices=ActivityType.choices(), primary_key=True)

    class Meta:
        db_table = "main_app_activity"
