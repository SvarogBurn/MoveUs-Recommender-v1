from django.db import migrations, models

# Plain-int copy of the removed shared.enums.PrivacySetting.EMAIL value.
EMAIL_SETTING = 3


def remove_email_privacy_setting(apps, schema_editor):
    UserPrivacySetting = apps.get_model("main", "UserPrivacySetting")
    UserPrivacySetting.objects.filter(setting=EMAIL_SETTING).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0018_backfill_privacy_settings"),
    ]

    operations = [
        migrations.RunPython(
            remove_email_privacy_setting, migrations.RunPython.noop
        ),
        migrations.AlterField(
            model_name="userprivacysetting",
            name="setting",
            field=models.SmallIntegerField(
                choices=[
                    (0, "LOCATION"),
                    (1, "AGE"),
                    (2, "FOLLOWERS"),
                    (4, "GENDER"),
                    (5, "POSTS"),
                ]
            ),
        ),
    ]
