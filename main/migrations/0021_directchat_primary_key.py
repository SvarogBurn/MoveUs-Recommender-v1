from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0020_alter_eventmember_has_participated'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE main_app_directchat "
                "ADD CONSTRAINT main_app_directchat_pkey "
                "PRIMARY KEY (user_1_id, user_2_id);"
            ),
            reverse_sql=(
                "ALTER TABLE main_app_directchat "
                "DROP CONSTRAINT main_app_directchat_pkey;"
            ),
        ),
    ]
