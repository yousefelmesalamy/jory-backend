from django.db import migrations, models


def medium_dark_to_medium(apps, schema_editor):
    CoffeeProfile = apps.get_model("catalog", "CoffeeProfile")
    CoffeeProfile.objects.filter(roast_level="MEDIUM_DARK").update(roast_level="MEDIUM")


class Migration(migrations.Migration):

    dependencies = [("catalog", "0014_coffeeprofile_tasting_notes_ar")]

    operations = [
        migrations.RunPython(medium_dark_to_medium, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="coffeeprofile",
            name="roast_level",
            field=models.CharField(
                blank=True,
                choices=[("LIGHT", "Light"), ("MEDIUM", "Medium"), ("DARK", "Dark")],
                max_length=20,
            ),
        ),
    ]
