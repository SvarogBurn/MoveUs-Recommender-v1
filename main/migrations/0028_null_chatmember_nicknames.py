from django.db import migrations


def null_nicknames(apps, schema_editor):
    ChatMember = apps.get_model("main", "ChatMember")
    ChatMember.objects.update(nickname=None)


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0027_alter_chatmember_nickname"),
    ]

    operations = [
        migrations.RunPython(null_nicknames, migrations.RunPython.noop),
    ]
