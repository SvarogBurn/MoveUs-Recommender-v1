from django.db import migrations


def add_pk(apps, schema_editor):
    from django.db import connection
    if "main_app_directchat" not in connection.introspection.table_names():
        return
    schema_editor.execute(
        "ALTER TABLE main_app_directchat "
        "ADD CONSTRAINT main_app_directchat_pkey "
        "PRIMARY KEY (user_1_id, user_2_id);"
    )


def drop_pk(apps, schema_editor):
    from django.db import connection
    if "main_app_directchat" not in connection.introspection.table_names():
        return
    schema_editor.execute(
        "ALTER TABLE main_app_directchat "
        "DROP CONSTRAINT main_app_directchat_pkey;"
    )


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0020_alter_eventmember_has_participated'),
    ]

    operations = [
        migrations.RunPython(add_pk, drop_pk),
    ]
