from collections import Counter

import django.db.models.deletion
from django.db import migrations, models


def dedupe_shared_locations(apps, schema_editor):
    Event = apps.get_model("main", "Event")
    Location = apps.get_model("main", "Location")

    counts = Counter(Event.objects.values_list("location_id", flat=True))
    shared_ids = [loc_id for loc_id, n in counts.items() if n > 1]
    if not shared_ids:
        return

    for loc_id in shared_ids:
        events = list(Event.objects.filter(location_id=loc_id).order_by("id"))
        # Keep the first event pointing at the original; clone for the rest.
        for event in events[1:]:
            original = Location.objects.get(pk=loc_id)
            original.pk = None
            original.save()
            event.location_id = original.pk
            event.save(update_fields=["location"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0022_fix_eventmember_participates"),
    ]

    operations = [
        migrations.RunPython(dedupe_shared_locations, noop_reverse),
        migrations.AlterField(
            model_name="event",
            name="location",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="event",
                to="main.location",
            ),
        ),
    ]
