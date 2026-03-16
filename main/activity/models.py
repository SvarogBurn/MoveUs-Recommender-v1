from django.db import models

from shared.enums import ActivityKind


class Activity(models.Model):
    id = models.SmallIntegerField(choices=ActivityKind.choices(), primary_key=True)

    class Meta:
        db_table = "main_app_activity"
