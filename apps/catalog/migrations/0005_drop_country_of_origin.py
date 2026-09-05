import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("catalog", "0004_backfill_origin")]

    operations = [
        migrations.AlterField(
            model_name="coffeeprofile",
            name="origin",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="coffee_profiles",
                to="catalog.origin",
            ),
        ),
        migrations.RemoveField(model_name="coffeeprofile", name="country_of_origin"),
    ]
