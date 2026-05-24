from django.db import migrations, models


def backfill_participates(apps, schema_editor):
    EventMember = apps.get_model("main", "EventMember")
    # MemberRole.PARTICIPANT = 1
    EventMember.objects.filter(role=1).update(participates=True)
    EventMember.objects.exclude(role=1).update(participates=False)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0021_directchat_primary_key"),
    ]

    operations = [
        migrations.AlterField(
            model_name="eventmember",
            name="participates",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(backfill_participates, noop_reverse),
    ]
