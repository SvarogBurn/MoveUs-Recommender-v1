from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0013_alter_location_address_line_1_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE main_app_event DROP COLUMN IF EXISTS cancelled;',
            reverse_sql='ALTER TABLE main_app_event ADD COLUMN cancelled boolean NOT NULL DEFAULT false;',
        ),
    ]
