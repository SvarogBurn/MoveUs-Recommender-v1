from django.db import migrations

# Plain-int copies of shared.enums to keep the migration self-contained.
FOLLOWERS_SCOPE = 1
MUTUALS_SCOPE = 3

# Mirrors main.user.services.DEFAULT_PRIVACY_SCOPES (setting value -> scope value).
DEFAULT_PRIVACY_SCOPES = {
    0: 1,  # LOCATION  -> FOLLOWERS
    1: 1,  # AGE       -> FOLLOWERS
    2: 2,  # FOLLOWERS -> EVERYONE
    3: 0,  # EMAIL     -> NOONE
    4: 1,  # GENDER    -> FOLLOWERS
    5: 2,  # POSTS     -> EVERYONE
}


def backfill_privacy_settings(apps, schema_editor):
    User = apps.get_model("main", "User")
    UserPrivacySetting = apps.get_model("main", "UserPrivacySetting")

    # Drop any rows for settings that no longer exist.
    UserPrivacySetting.objects.exclude(
        setting__in=DEFAULT_PRIVACY_SCOPES.keys()
    ).delete()

    # 1. Existing FOLLOWERS-scoped rows meant "mutual follows" under the old
    #    check_privacy logic. Remap them to the new MUTUALS scope so the prior
    #    privacy intent is preserved. Done before the backfill so freshly
    #    created rows keep their intended FOLLOWERS default.
    UserPrivacySetting.objects.filter(scope=FOLLOWERS_SCOPE).update(
        scope=MUTUALS_SCOPE
    )

    # 2. Create any missing rows (users with no settings, and the new POSTS
    #    setting) using the per-setting defaults.
    existing = set(UserPrivacySetting.objects.values_list("user_id", "setting"))
    rows = [
        UserPrivacySetting(user_id=user_id, setting=setting, scope=scope)
        for user_id in User.objects.values_list("id", flat=True)
        for setting, scope in DEFAULT_PRIVACY_SCOPES.items()
        if (user_id, setting) not in existing
    ]
    UserPrivacySetting.objects.bulk_create(rows, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0017_alter_userprivacysetting_scope_and_more"),
    ]

    operations = [
        migrations.RunPython(
            backfill_privacy_settings, migrations.RunPython.noop
        ),
    ]
