from django.db import migrations, models


def backfill_usernames(apps, schema_editor):
    """Derive a username from the email local-part for rows that predate this
    field, disambiguating collisions with a numeric suffix."""
    User = apps.get_model("accounts", "User")
    seen = set()
    for user in User.objects.all().order_by("id"):
        base = user.email.split("@")[0] or f"user{user.id}"
        candidate = base
        suffix = 1
        while candidate in seen or User.objects.filter(username=candidate).exclude(pk=user.pk).exists():
            suffix += 1
            candidate = f"{base}{suffix}"
        seen.add(candidate)
        user.username = candidate
        user.save(update_fields=["username"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="username",
            field=models.CharField(default="", max_length=150),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_usernames, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(max_length=150, unique=True),
        ),
    ]
