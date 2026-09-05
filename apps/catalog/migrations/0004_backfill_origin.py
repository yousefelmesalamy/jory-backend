from django.db import migrations
from django.utils.text import slugify


def country_names_to_origins(apps, schema_editor):
    CoffeeProfile = apps.get_model("catalog", "CoffeeProfile")
    Origin = apps.get_model("catalog", "Origin")

    for profile in CoffeeProfile.objects.exclude(country_of_origin=""):
        name = profile.country_of_origin.strip()
        origin, _ = Origin.objects.get_or_create(name=name, defaults={"slug": slugify(name)})
        profile.origin = origin
        profile.save(update_fields=["origin"])


def origins_back_to_country_names(apps, schema_editor):
    CoffeeProfile = apps.get_model("catalog", "CoffeeProfile")

    for profile in CoffeeProfile.objects.filter(origin__isnull=False).select_related("origin"):
        profile.country_of_origin = profile.origin.name
        profile.save(update_fields=["country_of_origin"])


class Migration(migrations.Migration):

    dependencies = [("catalog", "0003_origin")]

    operations = [
        migrations.RunPython(country_names_to_origins, origins_back_to_country_names),
    ]
