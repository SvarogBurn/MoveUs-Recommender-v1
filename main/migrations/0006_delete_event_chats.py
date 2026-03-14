from django.db import migrations


def delete_event_chats(apps, schema_editor):
    Event = apps.get_model("main", "Event")
    Chat = apps.get_model("main", "Chat")

    chat_ids = list(
        Event.objects.filter(chat__isnull=False).values_list("chat_id", flat=True)
    )

    if chat_ids:
        Event.objects.filter(chat_id__in=chat_ids).update(chat=None)
        Chat.objects.filter(id__in=chat_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0005_alter_commentlike_unique_together_remove_postlike_id_and_more"),
    ]

    operations = [
        migrations.RunPython(delete_event_chats, migrations.RunPython.noop),
    ]
