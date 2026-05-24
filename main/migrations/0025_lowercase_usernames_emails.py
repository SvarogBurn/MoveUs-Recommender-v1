from django.db import migrations


def lowercase_users(apps, schema_editor):
    """Normalize existing rows so case-insensitive duplicate detection at
    sign-up matches what's actually stored. Collisions (e.g. both 'Foo' and
    'foo' exist) are left untouched; an admin needs to resolve those by
    hand before the offending account can be cleaned up.
    """
    User = apps.get_model("main", "User")
    EmailAddress = apps.get_model("account", "EmailAddress")

    seen_usernames: set[str] = set()
    seen_emails: set[str] = set()
    for username, email in User.objects.values_list("username", "email"):
        if username == username.lower():
            seen_usernames.add(username)
        if email and email == email.lower():
            seen_emails.add(email)

    for user in User.objects.iterator():
        update_fields = []

        lowered_username = user.username.lower()
        if user.username != lowered_username and lowered_username not in seen_usernames:
            user.username = lowered_username
            seen_usernames.add(lowered_username)
            update_fields.append("username")

        if user.email:
            lowered_email = user.email.lower()
            if user.email != lowered_email and lowered_email not in seen_emails:
                user.email = lowered_email
                seen_emails.add(lowered_email)
                update_fields.append("email")

        if update_fields:
            user.save(update_fields=update_fields)

    seen_account_emails: set[tuple[int, str]] = set()
    for ea_email, ea_user_id in EmailAddress.objects.values_list("email", "user_id"):
        if ea_email == ea_email.lower():
            seen_account_emails.add((ea_user_id, ea_email))

    for ea in EmailAddress.objects.iterator():
        lowered = ea.email.lower()
        if ea.email == lowered:
            continue
        key = (ea.user_id, lowered)
        if key in seen_account_emails:
            continue
        ea.email = lowered
        ea.save(update_fields=["email"])
        seen_account_emails.add(key)


def noop_reverse(apps, schema_editor):
    # Lowercasing is one-way; original casing isn't recoverable.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0024_alter_event_description"),
        ("account", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(lowercase_users, noop_reverse),
    ]
