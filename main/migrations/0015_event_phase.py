from django.db import migrations, models
from django.utils import timezone


def backfill_phase(apps, schema_editor):
    Event = apps.get_model("main", "Event")
    now = timezone.now()
    for event in Event.objects.all().only(
        "id", "finished", "start_time", "end_time"
    ):
        if event.finished:
            phase = 2  # FINISHED
        elif event.end_time and event.end_time < now:
            phase = 2  # FINISHED
        elif event.start_time <= now:
            phase = 1  # IN_PROGRESS
        else:
            phase = 0  # SCHEDULED
        Event.objects.filter(id=event.id).update(phase=phase)


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0014_drop_event_cancelled"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="phase",
            field=models.SmallIntegerField(
                choices=[
                    (0, "SCHEDULED"),
                    (1, "IN_PROGRESS"),
                    (2, "FINISHED"),
                    (3, "CANCELLED"),
                ],
                default=0,
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="start_task_id",
            field=models.CharField(max_length=64, null=True, blank=True),
        ),
        migrations.AddField(
            model_name="event",
            name="end_task_id",
            field=models.CharField(max_length=64, null=True, blank=True),
        ),
        migrations.RunPython(backfill_phase, reverse_code=migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="event",
            name="finished",
        ),
    ]
